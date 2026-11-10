"""AI CEO and Executive Orchestrator for AI-COMPANY."""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from config.settings import settings
from infrastructure.database import db
from infrastructure.task_queue import task_queue
from infrastructure.scheduler import scheduler
from infrastructure.monitoring import system_monitor
from tool_factory.registry import tool_registry
from director.planner import strategic_planner
from director.performance import performance_director
from director.delegation import delegation_manager

# Import specialized agents
from agents.research.agent import ResearchAgent
from agents.engineering.agent import EngineeringAgent
from agents.marketing.agent import MarketingAgent
from agents.analytics.agent import AnalyticsAgent
from agents.operations.agent import OperationsAgent
from agents.quality.agent import QualitySecurityAgent

logger = logging.getLogger("ai_company.director.ceo")


class AICEO:
    """The Chief Executive Officer / Main Director of the Autonomous AI Organization."""

    def __init__(self):
        self.is_initialized = False
        self._autonomous_running = False
        self._loop_task: Optional[asyncio.Task] = None

        # Instantiate specialized autonomous employees
        self.research_agent = ResearchAgent()
        self.engineering_agent = EngineeringAgent()
        self.marketing_agent = MarketingAgent()
        self.analytics_agent = AnalyticsAgent()
        self.operations_agent = OperationsAgent()
        self.quality_agent = QualitySecurityAgent()

    async def initialize(self) -> None:
        """Initialize database, register agents, seed starting tools and objectives."""
        if self.is_initialized:
            return

        logger.info("Initializing Autonomous AI Enterprise...")

        # 1. Initialize SQLite Database
        await db.init_db()

        # 2. Register all 6 specialized employees with Task Queue
        task_queue.register_agent("research", self.research_agent)
        task_queue.register_agent("engineering", self.engineering_agent)
        task_queue.register_agent("marketing", self.marketing_agent)
        task_queue.register_agent("analytics", self.analytics_agent)
        task_queue.register_agent("operations", self.operations_agent)
        task_queue.register_agent("quality", self.quality_agent)

        # 3. Seed Default Objectives, Schedules, and Tools
        await db.seed_objectives_if_empty()
        await tool_registry.seed_built_in_tools()
        await scheduler.seed_default_schedules()

        self.is_initialized = True
        logger.info("AI Enterprise successfully initialized and operational.")

    async def run_cycle(self) -> Dict[str, Any]:
        """Execute one complete end-to-end autonomous corporate cycle."""
        if not self.is_initialized:
            await self.initialize()

        cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow()
        logger.info(f"--- Starting Autonomous Executive Cycle [{cycle_id}] ---")

        # Step 1: Check persistent scheduler for due recurring tasks
        scheduled_tasks_triggered = await scheduler.check_and_trigger()

        # Step 2: Check active strategic objectives and break down tasks if needed
        objectives = await db.get_objectives(status="active")
        new_tasks_created = 0

        for obj in objectives:
            # Check how many tasks exist for this objective
            existing_tasks = await db.fetch_all(
                "SELECT COUNT(*) as count FROM tasks WHERE objective_id = ?",
                (obj["id"],)
            )
            count = existing_tasks[0]["count"] if existing_tasks else 0

            # If no tasks exist for this active objective, deconstruct it
            if count == 0:
                logger.info(f"Deconstructing active objective: {obj['title']}")
                subtasks = await strategic_planner.deconstruct_objective(obj)
                for st in subtasks:
                    await task_queue.submit_task(
                        owner_agent=st.get("agent", "research"),
                        title=st.get("title", "Untitled Subtask"),
                        description=st.get("description", st.get("title", "")),
                        priority=st.get("priority", "medium"),
                        permission_level=st.get("permission_level", 1),
                        objective_id=obj["id"]
                    )
                    new_tasks_created += 1

        # Step 3: Review pending Level 3 approvals (Director sign-off)
        pending_approvals = await db.get_pending_approvals()
        approved_by_director = 0
        for appr in pending_approvals:
            # Director can approve Level 3 actions (Level 4 strictly requires Owner)
            if appr["permission_level"] <= 3:
                await db.update_approval(
                    approval_id=appr["id"],
                    status="approved",
                    reviewed_by="director",
                    comment="Approved by AI Director under Level 3 operational authority."
                )
                # Unblock associated task
                if appr.get("task_id"):
                    await db.update_task(appr["task_id"], status="pending")
                approved_by_director += 1

        # Step 4: Dispatch pending tasks to agents
        dispatched_task_ids = await task_queue.dispatch_next_batch(batch_size=6)

        # Wait briefly for synchronous steps to settle
        if dispatched_task_ids:
            await asyncio.sleep(0.5)

        # Step 5: Evaluate organizational performance & update objectives
        eval_result = await performance_director.evaluate_organization()
        
        # Update progress for active objectives based on task completions
        for obj in objectives:
            tasks = await db.fetch_all("SELECT status FROM tasks WHERE objective_id = ?", (obj["id"],))
            if tasks:
                completed = sum(1 for t in tasks if t["status"] == "completed")
                progress = int((completed / len(tasks)) * 100)
                new_status = "completed" if progress >= 100 else "active"
                await db.update_objective_progress(obj["id"], progress, new_status)

        cycle_duration = round((datetime.utcnow() - start_time).total_seconds(), 2)
        summary = {
            "cycle_id": cycle_id,
            "duration_seconds": cycle_duration,
            "scheduled_tasks_triggered": scheduled_tasks_triggered,
            "new_tasks_planned": new_tasks_created,
            "tasks_dispatched": len(dispatched_task_ids),
            "level3_approvals_granted": approved_by_director,
            "active_objectives_count": len(objectives),
            "health_verdict": eval_result.get("health_summary", {}).get("status", "healthy")
        }

        await db.log_audit(
            actor="director",
            action="executive_cycle",
            details=summary
        )

        logger.info(f"--- Cycle [{cycle_id}] Completed in {cycle_duration}s ---")
        return summary

    async def submit_owner_objective(
        self,
        title: str,
        description: str,
        priority: str = "high",
        target_agent: str = "director",
        kpis: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Inject a new high-level strategic business objective from the Owner."""
        if not self.is_initialized:
            await self.initialize()

        obj_id = f"OBJ-{uuid.uuid4().hex[:6].upper()}"
        obj_record = {
            "id": obj_id,
            "title": title,
            "description": description,
            "priority": priority,
            "target_agent": target_agent,
            "status": "active",
            "progress": 0,
            "kpis": kpis or ["Execute strategic deliverables to completion"]
        }
        await db.create_objective(obj_record)
        await db.log_audit(
            actor="owner",
            action="create_objective",
            details={"id": obj_id, "title": title}
        )

        # Trigger immediate deconstruction
        subtasks = await strategic_planner.deconstruct_objective(obj_record)
        created_tasks = []
        for st in subtasks:
            t = await task_queue.submit_task(
                owner_agent=st.get("agent", "research"),
                title=st.get("title", "Untitled Subtask"),
                description=st.get("description", st.get("title", "")),
                priority=st.get("priority", "medium"),
                permission_level=st.get("permission_level", 1),
                objective_id=obj_id
            )
            created_tasks.append(t["id"])

        return {
            "objective": obj_record,
            "subtasks_created": len(created_tasks),
            "task_ids": created_tasks
        }

    async def run_autonomous_loop(self) -> None:
        """Continuous background autonomous operational loop."""
        self._autonomous_running = True
        scheduler.start()
        logger.info("Autonomous enterprise engine running in background.")

        while self._autonomous_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Error during autonomous cycle: {e}")
            await asyncio.sleep(settings.AUTONOMOUS_CYCLE_INTERVAL_SECONDS)

    def start_background_engine(self) -> None:
        """Start background loop as an asyncio task."""
        if not self._autonomous_running:
            self._loop_task = asyncio.create_task(self.run_autonomous_loop())

    def stop_background_engine(self) -> None:
        """Stop background autonomous loop."""
        self._autonomous_running = False
        scheduler.stop()
        if self._loop_task:
            self._loop_task.cancel()


# Global CEO director singleton
ceo = AICEO()
