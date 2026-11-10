"""Agent Performance Evaluation and Capability Gap Detection."""

import logging
from typing import Dict, Any, List
from infrastructure.database import db
from infrastructure.monitoring import system_monitor
from tool_factory.builder import tool_builder

logger = logging.getLogger("ai_company.director.performance")


class PerformanceDirector:
    """Supervises division effectiveness, detects bottlenecks, and triggers capability upgrades."""

    async def evaluate_organization(self) -> Dict[str, Any]:
        """Review health metrics and detect capability gaps."""
        scorecards = await system_monitor.get_agent_scorecards()
        health = await system_monitor.get_company_health_summary()

        bottlenecks = []
        for sc in scorecards:
            if sc["failed"] > 0 and sc["success_rate_pct"] < 80.0:
                bottlenecks.append({
                    "agent": sc["agent"],
                    "reason": f"Success rate dropped to {sc['success_rate_pct']}% with {sc['failed']} failures."
                })

        return {
            "health_summary": health,
            "agent_scorecards": scorecards,
            "bottlenecks": bottlenecks,
            "recommendation": "Expand automated tooling" if bottlenecks else "Operations running smoothly"
        }

    async def auto_resolve_capability_gap(self, missing_capability: str, requesting_agent: str) -> Dict[str, Any]:
        """Automatically commission the Engineering Agent & Tool Factory to build a needed tool."""
        logger.info(f"Commissioning tool builder for capability gap: '{missing_capability}' requested by {requesting_agent}")
        tool_name = f"auto_{missing_capability.lower().replace(' ', '_')}"[:25]
        
        return await tool_builder.build_tool_from_specification(
            name=tool_name,
            description=f"Autonomously synthesized capability: {missing_capability} for {requesting_agent}",
            category="autonomous_expansion",
            author_agent="engineering"
        )


# Global performance director singleton
performance_director = PerformanceDirector()
