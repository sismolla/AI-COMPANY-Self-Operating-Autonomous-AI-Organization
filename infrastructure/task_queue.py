"""Persistent Task Queue and Dispatcher for AI-COMPANY."""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from infrastructure.database import db
from infrastructure.permissions import permission_engine
from config.settings import settings

logger = logging.getLogger("ai_company.task_queue")


class TaskQueue:
    """Orchestrates persistent task scheduling, queuing, and agent execution."""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.agent_registry: Dict[str, Any] = {}
        self._dispatcher_running = False
        self._lock = asyncio.Lock()

    def register_agent(self, agent_name: str, agent_instance: Any) -> None:
        """Register an agent worker instance."""
        self.agent_registry[agent_name] = agent_instance
        logger.info(f"Registered agent handler: {agent_name}")

    async def submit_task(
        self,
        owner_agent: str,
        title: str,
        description: str,
        priority: str = "medium",
        permission_level: int = 1,
        objective_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        delegation_depth: int = 0
    ) -> Dict[str, Any]:
        """Submit a new task to persistent queue with recursion depth checks."""
        # Enforce max delegation depth to prevent runaway agent loops
        MAX_DELEGATION_DEPTH = 2
        if delegation_depth > MAX_DELEGATION_DEPTH:
            raise ValueError(
                f"Task delegation depth exceeded maximum limit of {MAX_DELEGATION_DEPTH}. "
                f"Parent task: {parent_task_id}, Requested agent: {owner_agent}."
            )

        task_id = f"task_{uuid.uuid4().hex[:10]}"
        now = datetime.utcnow().isoformat()
        
        task_record = {
            "id": task_id,
            "objective_id": objective_id,
            "owner_agent": owner_agent,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "permission_level": permission_level,
            "inputs": inputs or {},
            "outputs": {},
            "error": None,
            "retry_count": 0,
            "max_retries": settings.MAX_RETRIES,
            "parent_task_id": parent_task_id,
            "delegation_depth": delegation_depth,
            "scheduled_at": scheduled_at,
            "created_at": now
        }
        await db.create_task(task_record)
        await db.log_audit(
            actor="task_queue",
            action="submit_task",
            details={"task_id": task_id, "agent": owner_agent, "title": title, "delegation_depth": delegation_depth}
        )
        return task_record

    async def recover_orphaned_tasks(self) -> int:
        """Recover tasks left in 'running' state after server restart, reload, or crash."""
        async with self._lock:
            running_db_tasks = await db.fetch_all("SELECT id, retry_count, max_retries FROM tasks WHERE status = 'running'")
            recovered = 0
            for t in running_db_tasks:
                tid = t["id"]
                if tid not in self.running_tasks or self.running_tasks[tid].done():
                    if t.get("retry_count", 0) < t.get("max_retries", settings.MAX_RETRIES):
                        await db.update_task(tid, status="pending")
                        recovered += 1
                    else:
                        await db.update_task(tid, status="failed", error="Execution interrupted / orphaned")
            if recovered > 0:
                logger.info(f"Recovered {recovered} orphaned tasks back to pending queue.")
            return recovered

    async def dispatch_next_batch(self, batch_size: int = 6, wait_for_completion: bool = False) -> List[str]:
        """Fetch pending tasks and dispatch to corresponding agent workers."""
        async with self._lock:
            pending_tasks = await db.get_pending_tasks(limit=batch_size)
            dispatched = []

            for task in pending_tasks:
                task_id = task["id"]
                agent_name = task["owner_agent"]

                # Check if task is already running
                if task_id in self.running_tasks and not self.running_tasks[task_id].done():
                    continue

                # Check permission clearance
                perm_level = task.get("permission_level", 1)
                if perm_level >= 3:
                    # Check if approval is already granted
                    approvals = await db.fetch_all(
                        "SELECT status FROM approvals WHERE task_id = ?",
                        (task_id,)
                    )
                    has_approval = any(a["status"] == "approved" for a in approvals)
                    if not has_approval:
                        await db.update_task(task_id, status="blocked_approval")
                        await db.create_approval({
                            "id": f"app_{uuid.uuid4().hex[:8]}",
                            "task_id": task_id,
                            "requested_by": agent_name,
                            "action_name": task["title"],
                            "permission_level": perm_level,
                            "payload": task.get("inputs", {})
                        })
                        logger.info(f"Task {task_id} requires Level {perm_level} approval. Marked blocked_approval.")
                        continue

                # Agent must be registered
                agent = self.agent_registry.get(agent_name)
                if not agent:
                    logger.warning(f"No agent registered for '{agent_name}'. Leaving task pending.")
                    continue

                # Launch async worker task
                coro = self._execute_task_wrapper(task, agent)
                bg_task = asyncio.create_task(coro)
                self.running_tasks[task_id] = bg_task
                dispatched.append(task_id)

        if wait_for_completion and dispatched:
            tasks_to_wait = [self.running_tasks[tid] for tid in dispatched if tid in self.running_tasks]
            if tasks_to_wait:
                await asyncio.gather(*tasks_to_wait, return_exceptions=True)

        return dispatched

    async def _execute_task_wrapper(self, task: Dict[str, Any], agent: Any) -> None:
        """Execute task with timeout, failure recovery, and metric logging."""
        task_id = task["id"]
        agent_name = task["owner_agent"]
        start_time = datetime.utcnow()
        await db.update_task(task_id, status="running", started_at=start_time.isoformat())

        try:
            # Execute within timeout limit
            output = await asyncio.wait_for(
                agent.execute_task(task),
                timeout=float(settings.TASK_TIMEOUT_SECONDS)
            )

            # Automated Quality Gate: Verify physical existence & non-empty status of claimed deliverables
            await self._verify_deliverables_quality_gate(task, output, agent_name)

            duration = (datetime.utcnow() - start_time).total_seconds()
            
            await db.update_task(
                task_id,
                status="completed",
                outputs=output or {},
                completed_at=datetime.utcnow().isoformat()
            )
            await db.record_metric(agent_name, "task_execution_time", duration, unit="seconds")
            await db.record_metric(agent_name, "task_success", 1.0, unit="count")
            await db.log_audit(
                actor=agent_name,
                action="complete_task",
                details={"task_id": task_id, "duration": duration}
            )

        except asyncio.TimeoutError:
            logger.error(f"Task {task_id} timed out after {settings.TASK_TIMEOUT_SECONDS}s.")
            await self._handle_task_failure(task, f"Execution timed out ({settings.TASK_TIMEOUT_SECONDS}s)")
        except Exception as e:
            logger.exception(f"Task {task_id} failed with error: {e}")
            await self._handle_task_failure(task, str(e))
        finally:
            self.running_tasks.pop(task_id, None)

    async def _verify_deliverables_quality_gate(self, task: Dict[str, Any], output: Any, agent_name: str) -> None:
        """Automated Quality Gate: Asserts that all claimed deliverable files physically exist and are non-empty."""
        if not isinstance(output, dict):
            return

        claimed_files = []
        for file_key in ["saved_script", "saved_plan", "saved_report", "saved_audit", "saved_file", "saved_ops_log"]:
            fval = output.get(file_key)
            if fval and isinstance(fval, str):
                claimed_files.append(fval)

        ws_dir = (settings.WORKSPACE_DIR / agent_name).resolve()
        for filename in claimed_files:
            file_path = (ws_dir / filename).resolve()
            if not file_path.exists():
                raise FileNotFoundError(
                    f"[QUALITY GATE FAILED] Claimed deliverable '{filename}' was not created on disk by agent '{agent_name}'."
                )
            if file_path.stat().st_size == 0:
                raise ValueError(
                    f"[QUALITY GATE FAILED] Claimed deliverable '{filename}' is empty (0 bytes) in '{agent_name}' workspace."
                )

        if claimed_files:
            logger.info(f"[QUALITY GATE PASSED] Verified {len(claimed_files)} deliverable files for task '{task.get('id')}'.")

    async def _handle_task_failure(self, task: Dict[str, Any], error_msg: str) -> None:
        """Handle retry and error recording."""
        task_id = task["id"]
        retry_count = task.get("retry_count", 0) + 1
        max_retries = task.get("max_retries", settings.MAX_RETRIES)
        agent_name = task["owner_agent"]

        await db.record_metric(agent_name, "task_failure", 1.0, unit="count")

        if retry_count < max_retries:
            logger.info(f"Retrying task {task_id} (Attempt {retry_count}/{max_retries})...")
            await db.update_task(
                task_id,
                status="pending",
                retry_count=retry_count,
                error=f"Attempt {retry_count} failed: {error_msg}"
            )
        else:
            logger.error(f"Task {task_id} exceeded maximum retries. Marked as failed.")
            await db.update_task(
                task_id,
                status="failed",
                retry_count=retry_count,
                error=error_msg,
                completed_at=datetime.utcnow().isoformat()
            )


# Global task queue singleton
task_queue = TaskQueue()
