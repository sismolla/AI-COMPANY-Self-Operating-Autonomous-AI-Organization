"""Specialized Engineering & Tool Building Autonomous Agent."""

import logging
from typing import Dict, Any
from agents.base import BaseAgent
from tool_factory.builder import tool_builder

logger = logging.getLogger("ai_company.agent.engineering")


class EngineeringAgent(BaseAgent):
    """Builds software, writes tests, and autonomously manufactures new tools."""

    def __init__(self):
        super().__init__(
            name="engineering",
            role="Principal Software Engineer & Tool Architect",
            description="Designs, writes, tests, and deploys internal tools and automation software.",
            max_permission_level=2
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute engineering task, creating tools if requested."""
        inputs = task.get("inputs", {})
        tool_name = inputs.get("tool_name")
        tool_desc = inputs.get("tool_description")

        # If task explicitly requests tool synthesis
        if tool_name and tool_desc:
            build_res = await tool_builder.build_tool_from_specification(
                name=tool_name,
                description=tool_desc,
                category=inputs.get("category", "engineering"),
                author_agent="engineering"
            )
            return {
                "summary": f"Autonomously built tool '{tool_name}' with sandbox verification.",
                "tool_build_result": build_res,
                "status": "completed" if build_res.get("success") else "failed"
            }

        # Otherwise execute general engineering task
        result = await super().execute_task(task)
        
        # Write any generated code to workspace
        artifacts = result.get("artifacts")
        code = (artifacts.get("code") if isinstance(artifacts, dict) else None) or result.get("code")
        test_code = (artifacts.get("test_code") if isinstance(artifacts, dict) else None) or result.get("test_code")
        
        if code:
            try:
                fn = f"tool_{task.get('id', 'eng')}.py"
                self.write_workspace_file(fn, code)
                result["saved_script"] = fn
                result["saved_file"] = fn
                if test_code:
                    self.write_workspace_file(f"test_{fn}", test_code)
            except Exception as e:
                logger.warning(f"Could not save script file: {e}")

        return result
