"""Strategic Objective Planner and Work Breakdown Engine for AI Director."""

import json
import logging
from typing import Dict, Any, List
from infrastructure.llm_adapter import llm_adapter

logger = logging.getLogger("ai_company.director.planner")


class StrategicPlanner:
    """Deconstructs high-level business objectives into prioritized agent tasks."""

    async def deconstruct_objective(self, objective: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Break down high-level objective into concrete actionable subtasks."""
        obj_id = objective.get("id", "OBJ-GEN")
        title = objective.get("title", "")
        desc = objective.get("description", "")
        kpis = objective.get("kpis", [])

        prompt = f"""
You are the AI CEO / Director of an autonomous company.
Break down this strategic business objective into actionable tasks for our 6 specialized AI employees:
- research (market intelligence, competitors, data gathering)
- engineering (software tools, automation, APIs, tests)
- marketing (content strategy, campaigns, copywriting, audience)
- analytics (KPI tracking, performance metrics, conversion)
- operations (recurring sidecars, backups, queue hygiene)
- quality (security checks, code review, safety enforcement)

Strategic Objective: {title}
Description: {desc}
Success KPIs: {kpis}

Return a valid JSON object matching this schema:
{{
    "plan_summary": "Executive approach...",
    "subtasks": [
        {{
            "agent": "research | engineering | marketing | analytics | operations | quality",
            "title": "Clear task title",
            "description": "Specific deliverables and instructions",
            "priority": "critical | high | medium | low",
            "permission_level": 1 or 2
        }}
    ]
}}
"""
        response = await llm_adapter.complete(
            prompt=prompt,
            system_prompt="You are the AI Director planning strategic enterprise initiatives.",
            role="director",
            json_mode=True
        )

        plan_data = response.to_json()
        subtasks = plan_data.get("subtasks", [])

        # Default fallback tasks if LLM returned empty
        if not subtasks:
            subtasks = [
                {
                    "agent": "research",
                    "title": f"Market Opportunity Scan for {title}",
                    "description": f"Gather competitive landscape and actionable insights for {desc}",
                    "priority": "high",
                    "permission_level": 1
                },
                {
                    "agent": "engineering",
                    "title": f"Build Automation Tools for {title}",
                    "description": f"Develop scripts and data processors to support {title}",
                    "priority": "high",
                    "permission_level": 2
                },
                {
                    "agent": "marketing",
                    "title": f"Formulate Launch Campaign for {title}",
                    "description": f"Draft content strategy and audience engagement funnel for {title}",
                    "priority": "medium",
                    "permission_level": 2
                },
                {
                    "agent": "quality",
                    "title": f"Audit Policy & Code Safety for {title}",
                    "description": f"Verify least-privilege compliance and run AST safety checks",
                    "priority": "high",
                    "permission_level": 2
                }
            ]

        # Attach objective ID
        for t in subtasks:
            t["objective_id"] = obj_id

        return subtasks


# Global planner singleton
strategic_planner = StrategicPlanner()
