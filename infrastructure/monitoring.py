"""Monitoring, Observability, and Health Tracking for AI-COMPANY."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from infrastructure.database import db

logger = logging.getLogger("ai_company.monitoring")


class SystemMonitor:
    """Collects and synthesizes enterprise-wide telemetry, health, and KPIs."""

    async def get_company_health_summary(self) -> Dict[str, Any]:
        """Aggregate company-wide health statistics and metrics."""
        task_stats = await db.fetch_all(
            """
            SELECT status, COUNT(*) as count 
            FROM tasks 
            GROUP BY status
            """
        )
        task_counts = {r["status"]: r["count"] for r in task_stats}
        total_tasks = sum(task_counts.values())
        completed_tasks = task_counts.get("completed", 0)
        failed_tasks = task_counts.get("failed", 0)
        pending_tasks = task_counts.get("pending", 0)
        running_tasks = task_counts.get("running", 0)
        blocked_tasks = task_counts.get("blocked_approval", 0)

        success_rate = (completed_tasks / total_tasks * 100.0) if total_tasks > 0 else 100.0

        tools_count_res = await db.fetch_one("SELECT COUNT(*) as count FROM tools WHERE status = 'approved'")
        approved_tools = tools_count_res["count"] if tools_count_res else 0

        pending_appr_res = await db.fetch_one("SELECT COUNT(*) as count FROM approvals WHERE status = 'pending'")
        pending_approvals = pending_appr_res["count"] if pending_appr_res else 0

        avg_time_res = await db.fetch_one(
            "SELECT AVG(value) as avg_val FROM performance_metrics WHERE metric_name = 'task_execution_time'"
        )
        avg_latency = round(avg_time_res["avg_val"], 2) if (avg_time_res and avg_time_res["avg_val"]) else 0.0

        return {
            "status": "healthy" if failed_tasks <= completed_tasks else "degraded",
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "blocked_approval_tasks": blocked_tasks,
            "success_rate_pct": round(success_rate, 1),
            "approved_tools_count": approved_tools,
            "pending_approvals_count": pending_approvals,
            "avg_task_latency_sec": avg_latency,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_agent_scorecards(self) -> List[Dict[str, Any]]:
        """Calculate per-agent productivity and quality scorecards."""
        agents = ["director", "engineering", "research", "marketing", "analytics", "operations", "quality"]
        scorecards = []

        for agent in agents:
            stats = await db.fetch_all(
                """
                SELECT status, COUNT(*) as count
                FROM tasks
                WHERE owner_agent = ?
                GROUP BY status
                """,
                (agent,)
            )
            counts = {s["status"]: s["count"] for s in stats}
            total = sum(counts.values())
            completed = counts.get("completed", 0)
            failed = counts.get("failed", 0)
            rate = round((completed / total * 100.0), 1) if total > 0 else 100.0

            avg_dur = await db.fetch_one(
                """
                SELECT AVG(value) as avg_val FROM performance_metrics 
                WHERE agent_name = ? AND metric_name = 'task_execution_time'
                """,
                (agent,)
            )
            avg_sec = round(avg_dur["avg_val"], 2) if (avg_dur and avg_dur["avg_val"]) else 0.0

            scorecards.append({
                "agent": agent,
                "total_tasks": total,
                "completed": completed,
                "failed": failed,
                "success_rate_pct": rate,
                "avg_duration_sec": avg_sec,
                "health": "active" if total > 0 else "idle"
            })

        return scorecards


# Global monitor singleton
system_monitor = SystemMonitor()
