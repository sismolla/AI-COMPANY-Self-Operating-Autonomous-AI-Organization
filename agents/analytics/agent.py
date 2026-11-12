"""Specialized Analytics & Performance Autonomous Agent."""

import json
import logging
from typing import Dict, Any
from agents.base import BaseAgent
from integrations.analytics import analytics_integration
from infrastructure.monitoring import system_monitor

logger = logging.getLogger("ai_company.agent.analytics")


class AnalyticsAgent(BaseAgent):
    """Measures organization KPIs, identifies bottlenecks, and generates executive scorecards."""

    def __init__(self):
        super().__init__(
            name="analytics",
            role="Chief Analytics & Performance Officer",
            description="Computes division productivity, monitors health, and delivers optimization insights.",
            max_permission_level=2
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analytics task and compute executive scorecard."""
        telemetry = await analytics_integration.generate_executive_kpi_report()
        scorecards = await system_monitor.get_agent_scorecards()

        result = await super().execute_task(task)
        result["telemetry"] = telemetry
        result["agent_scorecards"] = scorecards

        # Save analytics report to workspace
        artifacts_val = result.get("artifacts", {})
        artifacts_str = json.dumps(artifacts_val, indent=2) if isinstance(artifacts_val, (dict, list)) else str(artifacts_val)
        report_fn = f"analytics_report_{task.get('id', 'latest')}.md"
        report_md = (
            f"# Performance & Analytics Report: {task.get('title')}\n\n"
            f"## Organizational Velocity\n"
            f"- Total Tasks Processed: {telemetry['total_tasks_processed']}\n"
            f"- Success Rate: {telemetry['tasks_completed']}/{telemetry['total_tasks_processed']}\n"
            f"- Active Tools: {telemetry['active_approved_tools']}\n"
            f"- Strategic Progress: {telemetry['average_objective_progress']}%\n\n"
            f"## Executive Summary\n{result.get('summary', '')}\n\n"
            f"## Strategic Projections & Unit Economics\n```json\n{artifacts_str}\n```\n"
        )
        try:
            self.write_workspace_file(report_fn, report_md)
            result["saved_report"] = report_fn
            result["saved_file"] = report_fn
        except Exception as e:
            logger.warning(f"Could not save analytics report: {e}")

        return result
