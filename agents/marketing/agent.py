"""Specialized Marketing & Content Autonomous Agent."""

import logging
from typing import Dict, Any
from agents.base import BaseAgent
from integrations.social_media import social_media

logger = logging.getLogger("ai_company.agent.marketing")


class MarketingAgent(BaseAgent):
    """Formulates content strategies, drafts campaign copy, and stages social posts."""

    def __init__(self):
        super().__init__(
            name="marketing",
            role="Head of Marketing & Audience Growth",
            description="Designs marketing strategies, writes multi-channel copy, and manages campaign funnels.",
            max_permission_level=2
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute marketing task and stage any generated social content."""
        result = await super().execute_task(task)

        # Stage social content if produced
        artifacts = result.get("artifacts", {})
        if isinstance(artifacts, dict) and "draft_posts" in artifacts:
            staged = []
            for p in artifacts.get("draft_posts", []):
                platform = p.get("channel", "general")
                copy = p.get("copy", "")
                staged_post = social_media.stage_post(
                    platform=platform,
                    content=copy,
                    author_agent=self.name
                )
                staged.append(staged_post)
            result["staged_posts"] = staged

        # Save campaign plan to workspace
        plan_filename = f"campaign_{task.get('id', 'plan')}.md"
        plan_content = f"# Marketing Campaign: {task.get('title')}\n\n{result.get('summary', '')}\n\n{result.get('artifacts', '')}"
        try:
            self.write_workspace_file(plan_filename, plan_content)
            result["saved_plan"] = plan_filename
        except Exception as e:
            logger.warning(f"Could not save campaign plan: {e}")

        return result
