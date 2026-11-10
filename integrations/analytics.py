"""Enterprise Analytics Aggregator Integration."""

import logging
from typing import Dict, Any, List
from infrastructure.database import db

logger = logging.getLogger("ai_company.analytics_integration")


class AnalyticsIntegration:
    """Computes organizational efficiency, task velocity, and KPI progress."""

    async def generate_executive_kpi_report(self) -> Dict[str, Any]:
        """Compile executive KPI metrics across all organizational divisions."""
        objectives = await db.get_objectives()
        tasks = await db.get_all_tasks(limit=200)
        tools = await db.get_approved_tools()

        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "completed")
        failed = sum(1 for t in tasks if t["status"] == "failed")
        active = sum(1 for t in tasks if t["status"] in ("running", "pending"))

        avg_progress = 0
        if objectives:
            avg_progress = sum(o["progress"] for o in objectives) // len(objectives)

        division_breakdown = {}
        for t in tasks:
            agent = t["owner_agent"]
            division_breakdown[agent] = division_breakdown.get(agent, 0) + 1

        return {
            "strategic_objectives_count": len(objectives),
            "average_objective_progress": avg_progress,
            "total_tasks_processed": total_tasks,
            "tasks_completed": completed,
            "tasks_failed": failed,
            "tasks_in_flight": active,
            "division_workload": division_breakdown,
            "active_approved_tools": len(tools),
            "health_verdict": "Optimal" if failed <= (completed * 0.1) else "Attention Needed"
        }


# Global analytics singleton
analytics_integration = AnalyticsIntegration()
