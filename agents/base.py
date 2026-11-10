"""Base Autonomous AI Employee Class for AI-COMPANY."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from config.settings import settings
from infrastructure.llm_adapter import llm_adapter
from infrastructure.memory import memory_store
from infrastructure.permissions import permission_engine
from infrastructure.database import db

logger = logging.getLogger("ai_company.agent_base")


class BaseAgent:
    """Base class for all autonomous AI employees in the organization."""

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        max_permission_level: int = 2
    ):
        self.name = name.lower()
        self.role = role
        self.description = description
        self.max_permission_level = max_permission_level
        self.workspace_dir = settings.WORKSPACE_DIR / self.name
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.instructions: str = ""
        self.load_instructions()

    def load_instructions(self) -> None:
        """Load role-specific instructions markdown file."""
        instr_file = settings.BASE_DIR / "agents" / self.name / "instructions.md"
        if instr_file.exists():
            with open(instr_file, "r", encoding="utf-8") as f:
                self.instructions = f.read()
        else:
            self.instructions = f"You are the {self.role}. {self.description}"

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using LLM reasoning, memory, tools, and workspace operations."""
        logger.info(f"Agent '{self.name}' starting task: {task.get('title')}")

        # 1. Recall contextual memory
        memory_context = await memory_store.build_context_prompt(self.name)

        # 2. Formulate prompt
        task_title = task.get("title", "")
        task_desc = task.get("description", "")
        task_inputs = json.dumps(task.get("inputs", {}), indent=2)

        prompt = f"""
Task: {task_title}
Objective Description: {task_desc}
Provided Inputs:
{task_inputs}

{memory_context}

Please execute this task thoroughly according to your role instructions.
Provide structured JSON with:
1. "summary": Executive summary of what was accomplished.
2. "status": "completed" or "needs_escalation"
3. "artifacts": Any key deliverables, text, code, or data points produced.
4. "learnings": Key insights or domain knowledge to persist in memory.
5. "delegations": List of any subtasks to delegate to other agents (optional).
"""
        response = await llm_adapter.complete(
            prompt=prompt,
            system_prompt=self.instructions,
            role=self.name,
            json_mode=True
        )

        output_data = response.to_json()

        # 3. Store learnings in episodic and long-term memory
        learnings = output_data.get("learnings")
        if learnings:
            await memory_store.save(
                agent_name=self.name,
                memory_type="long_term",
                key=f"task_{task.get('id', 'unknown')}_learnings",
                value=learnings,
                tags=[self.name, "task_execution"]
            )

        # Record episodic memory
        await memory_store.save(
            agent_name=self.name,
            memory_type="episodic",
            key=f"task_{task.get('id', 'unknown')}_result",
            value=output_data.get("summary", "Task executed"),
            tags=[self.name, task.get("priority", "medium")]
        )

        return output_data

    def write_workspace_file(self, rel_path: str, content: str) -> Path:
        """Write a file safely within agent's private workspace."""
        perm = permission_engine.check_permission(self.name, "write_workspace_file")
        if not perm.allowed:
            raise PermissionError(f"Agent '{self.name}' not authorized to write files.")
        
        target = (self.workspace_dir / rel_path).resolve()
        # Prevent path traversal outside workspace
        if not str(target).startswith(str(self.workspace_dir.resolve())):
            raise PermissionError(f"Access denied: Path {target} escapes agent workspace.")
        
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    def read_workspace_file(self, rel_path: str) -> str:
        """Read a file from agent's private workspace."""
        target = (self.workspace_dir / rel_path).resolve()
        if not target.exists() or not str(target).startswith(str(self.workspace_dir.resolve())):
            raise FileNotFoundError(f"File {rel_path} not found in workspace.")
        with open(target, "r", encoding="utf-8") as f:
            return f.read()

    def list_workspace_files(self) -> List[str]:
        """List relative file paths in workspace."""
        return [str(p.relative_to(self.workspace_dir)) for p in self.workspace_dir.glob("**/*") if p.is_file()]
