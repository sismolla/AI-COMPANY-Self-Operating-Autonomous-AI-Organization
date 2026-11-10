"""Inter-Agent Delegation Protocol and Message Routing."""

import logging
from typing import Dict, Any, Optional
from infrastructure.task_queue import task_queue
from infrastructure.database import db
from infrastructure.permissions import permission_engine

logger = logging.getLogger("ai_company.director.delegation")


class DelegationManager:
    """Coordinates structured work requests between specialized autonomous agents."""

    async def delegate(
        self,
        from_agent: str,
        to_agent: str,
        task_title: str,
        task_description: str,
        priority: str = "medium",
        inputs: Optional[Dict[str, Any]] = None,
        objective_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate and route an inter-agent task delegation."""
        logger.info(f"Delegation request: {from_agent} -> {to_agent} ('{task_title}')")

        # Determine permission level required for target action
        action_level = 2 if to_agent in ("engineering", "marketing", "operations") else 1

        # Enforce policy: agents cannot self-escalate beyond Level 2 without approval
        if action_level > 2:
            return {
                "success": False,
                "error": f"Delegation to {to_agent} requires Level {action_level} clearance. Must be approved by Director."
            }

        # Submit task into persistent queue
        task_record = await task_queue.submit_task(
            owner_agent=to_agent,
            title=f"[{from_agent.upper()} DELEGATION] {task_title}",
            description=f"Delegated by {from_agent}: {task_description}",
            priority=priority,
            permission_level=action_level,
            objective_id=objective_id,
            inputs=inputs or {}
        )

        await db.log_audit(
            actor=from_agent,
            action="delegate_task",
            details={
                "to_agent": to_agent,
                "task_id": task_record["id"],
                "task_title": task_title
            }
        )

        return {
            "success": True,
            "task_id": task_record["id"],
            "delegated_to": to_agent
        }


# Global delegation manager singleton
delegation_manager = DelegationManager()
