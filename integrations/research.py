"""Research and Market Intelligence Integration."""

import logging
from typing import Dict, Any, List
from integrations.browser import browser_automation
from infrastructure.llm_adapter import llm_adapter

logger = logging.getLogger("ai_company.research_integration")


class ResearchIntegration:
    """Collects, cleans, and extracts market intelligence."""

    async def gather_topic_intelligence(self, topic: str) -> Dict[str, Any]:
        """Fetch insights for a given research topic."""
        prompt = f"""
Perform comprehensive market research on the topic: '{topic}'.
Structure the response with:
1. Executive Summary
2. Key Market Drivers & Trends
3. Competitive Landscape
4. Strategic Opportunities for Autonomous Operations
5. Recommended Action Items
"""
        response = await llm_adapter.complete(
            prompt=prompt,
            system_prompt="You are an elite competitive intelligence researcher.",
            role="research",
            json_mode=True
        )
        data = response.to_json()
        return {
            "topic": topic,
            "intelligence": data,
            "model_used": response.model
        }


# Global research singleton
research_integration = ResearchIntegration()
