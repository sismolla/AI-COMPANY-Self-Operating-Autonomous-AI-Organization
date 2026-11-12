"""Specialized Research & Market Intelligence Autonomous Agent."""

import json
import logging
from typing import Dict, Any
from agents.base import BaseAgent
from integrations.research import research_integration
from infrastructure.memory import memory_store

logger = logging.getLogger("ai_company.agent.research")


class ResearchAgent(BaseAgent):
    """Conducts market analysis, competitive teardowns, and information synthesis."""

    def __init__(self):
        super().__init__(
            name="research",
            role="Lead Market & Intelligence Researcher",
            description="Scans digital markets, analyzes trends, and compiles structured briefs.",
            max_permission_level=1
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research task and persist intelligence in memory."""
        inputs = task.get("inputs", {})
        topic = inputs.get("topic") or task.get("title", "Digital Market Opportunities")

        # Gather topic intelligence
        research_data = await research_integration.gather_topic_intelligence(topic)

        # Standard execution loop
        result = await super().execute_task(task)
        result["research_intelligence"] = research_data

        # Save markdown dossier into persistent agent memory (Level 1 compliant)
        dossier_key = f"research_{task.get('id', 'dossier')}"
        artifacts_val = result.get('artifacts', {})
        insights_str = json.dumps(artifacts_val, indent=2) if isinstance(artifacts_val, (dict, list)) else str(artifacts_val)
        dossier_content = (
            f"# Intelligence Dossier: {topic}\n\n"
            f"## Summary\n{result.get('summary', '')}\n\n"
            f"## Key Strategic Insights\n{insights_str}\n"
        )
        await memory_store.save(
            agent_name=self.name,
            memory_type="long_term",
            key=dossier_key,
            value=dossier_content,
            tags=["research", topic]
        )
        result["saved_dossier_key"] = dossier_key
        result["dossier_content"] = dossier_content

        return result
