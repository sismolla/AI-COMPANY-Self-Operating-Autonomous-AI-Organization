"""Persistent Scheduler for AI-COMPANY.

Survives process restarts by persisting schedules and execution history in SQLite.
"""

import json
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from infrastructure.database import db
from infrastructure.task_queue import task_queue
from config.settings import settings

logger = logging.getLogger("ai_company.scheduler")


class PersistentScheduler:
    """Evaluates and triggers recurring business sidecars and cron tasks."""

    def __init__(self):
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    async def register_schedule(
        self,
        name: str,
        interval_seconds: int,
        target_agent: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        cron_expression: Optional[str] = None
    ) -> str:
        """Register or update a recurring schedule."""
        sched_id = f"sched_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow()
        next_run = (now + timedelta(seconds=interval_seconds)).isoformat()

        await db.execute(
            """
            INSERT OR REPLACE INTO schedules
            (id, name, cron_expression, interval_seconds, target_agent, action, payload_json, last_run_at, next_run_at, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sched_id,
                name,
                cron_expression,
                interval_seconds,
                target_agent,
                action,
                json.dumps(payload or {}),
                None,
                next_run,
                1,
                now.isoformat()
            )
        )
        logger.info(f"Registered recurring schedule '{name}' (every {interval_seconds}s) for {target_agent}.")
        return sched_id

    async def seed_default_schedules(self) -> None:
        """Seed default recurring corporate tasks if table is empty."""
        rows = await db.fetch_all("SELECT COUNT(*) as count FROM schedules")
        if rows and rows[0]["count"] == 0:
            defaults = [
                {
                    "name": "Hourly Operational Health & Queue Cleanup",
                    "interval_seconds": 3600,
                    "target_agent": "operations",
                    "action": "run_system_health_audit",
                    "payload": {"check_disk": True, "clean_stale_tasks": True}
                },
                {
                    "name": "Daily Market Intelligence Scan",
                    "interval_seconds": 86400,
                    "target_agent": "research",
                    "action": "daily_market_scan",
                    "payload": {"topics": ["AI agents", "autonomous workflows", "competitor moves"]}
                },
                {
                    "name": "Daily Executive Analytics KPI Report",
                    "interval_seconds": 86400,
                    "target_agent": "analytics",
                    "action": "generate_executive_report",
                    "payload": {"period": "daily"}
                },
                {
                    "name": "Weekly Content Strategy Generation",
                    "interval_seconds": 604800,
                    "target_agent": "marketing",
                    "action": "generate_weekly_content",
                    "payload": {"channels": ["twitter", "newsletter", "linkedin"]}
                }
            ]
            for d in defaults:
                await self.register_schedule(
                    name=d["name"],
                    interval_seconds=d["interval_seconds"],
                    target_agent=d["target_agent"],
                    action=d["action"],
                    payload=d["payload"]
                )

    async def check_and_trigger(self) -> int:
        """Scan active schedules and enqueue due tasks."""
        now_str = datetime.utcnow().isoformat()
        due_schedules = await db.fetch_all(
            """
            SELECT * FROM schedules 
            WHERE is_active = 1 AND (next_run_at IS NULL OR next_run_at <= ?)
            """,
            (now_str,)
        )

        triggered_count = 0
        for s in due_schedules:
            payload = json.loads(s["payload_json"])
            # Submit task to persistent queue
            await task_queue.submit_task(
                owner_agent=s["target_agent"],
                title=s["name"],
                description=f"Scheduled execution of {s['action']}",
                priority="medium",
                inputs=payload
            )
            # Calculate next run
            interval = s["interval_seconds"] or 3600
            next_run = (datetime.utcnow() + timedelta(seconds=interval)).isoformat()
            await db.execute(
                "UPDATE schedules SET last_run_at = ?, next_run_at = ? WHERE id = ?",
                (now_str, next_run, s["id"])
            )
            triggered_count += 1
            logger.info(f"Triggered scheduled task '{s['name']}' -> dispatched to {s['target_agent']}.")

        return triggered_count

    async def run_loop(self) -> None:
        """Background loop continuously checking schedules."""
        self._running = True
        logger.info("Persistent scheduler loop started.")
        while self._running:
            try:
                await self.check_and_trigger()
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}")
            await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)

    def start(self) -> None:
        if not self._running:
            self._loop_task = asyncio.create_task(self.run_loop())

    def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()


# Global scheduler singleton
scheduler = PersistentScheduler()
