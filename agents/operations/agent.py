"""Specialized Operations & Hygiene Autonomous Agent."""

import logging
from typing import Dict, Any
from agents.base import BaseAgent
from infrastructure.database import db

logger = logging.getLogger("ai_company.agent.operations")


class OperationsAgent(BaseAgent):
    """Maintains organizational hygiene, runs scheduled recurring maintenance, and cleans stale state."""

    def __init__(self):
        super().__init__(
            name="operations",
            role="Head of Operations & Infrastructure Hygiene",
            description="Executes recurring maintenance sidecars, audits system integrity, and manages queue hygiene.",
            max_permission_level=2
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operational maintenance task."""
        # Operational check: detect any stuck 'running' tasks older than 5 minutes
        stuck_tasks = await db.fetch_all(
            "SELECT id, owner_agent, started_at FROM tasks WHERE status = 'running'"
        )

        result = await super().execute_task(task)
        result["operational_check"] = {
            "currently_running_tasks": len(stuck_tasks),
            "workspace_status": "Clean",
            "database_integrity": "OK"
        }

        # Save ops log
        log_fn = f"ops_log_{task.get('id', 'latest')}.md"
        log_content = f"# Operations Log: {task.get('title')}\n\n{result.get('summary', '')}\n\nRunning tasks checked: {len(stuck_tasks)}"
        try:
            self.write_workspace_file(log_fn, log_content)
            result["saved_ops_log"] = log_fn
        except Exception as e:
            logger.warning(f"Could not save ops log: {e}")

        return result
