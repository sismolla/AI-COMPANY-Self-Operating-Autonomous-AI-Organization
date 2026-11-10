"""Permission and Security Enforcement Engine for AI-COMPANY."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel
from config.settings import settings


class ActionCheckResult(BaseModel):
    allowed: bool
    permission_level: int
    requires_approval: bool
    approved_by: Optional[str] = None
    reason: str


class PermissionEngine:
    """Enforces least-privilege policies across all autonomous agents."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (settings.CONFIG_DIR / "permissions.yaml")
        self.policy: Dict[str, Any] = {}
        self.load_policy()

    def load_policy(self) -> None:
        """Load or reload permission policies from yaml."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Permission policy file not found at {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f) or {}

    def get_action_permission_level(self, action_name: str) -> int:
        """Determine what permission level an action belongs to."""
        levels = self.policy.get("levels", {})
        for lvl_key, lvl_data in levels.items():
            if action_name in lvl_data.get("allowed_actions", []):
                # parse 'level_1' -> 1
                try:
                    return int(lvl_key.split("_")[-1])
                except (ValueError, IndexError):
                    return 2
        # Default unlisted actions to Level 3 (requires approval)
        return 3

    def check_permission(
        self,
        agent_name: str,
        action_name: str,
        target_path: Optional[str] = None
    ) -> ActionCheckResult:
        """Check if an agent is authorized to perform a specific action."""
        
        # Rule 1: Security policy files are IMMUTABLE to all agents (including Director)
        if target_path and "permissions.yaml" in target_path.lower():
            return ActionCheckResult(
                allowed=False,
                permission_level=4,
                requires_approval=True,
                approved_by="owner",
                reason="Security policy modification is strictly reserved for the human Owner."
            )

        agent_defaults = self.policy.get("agent_default_permissions", {}).get(agent_name, {})
        agent_max_level = agent_defaults.get("max_level", 1)
        action_level = self.get_action_permission_level(action_name)

        levels_data = self.policy.get("levels", {})
        level_key = f"level_{action_level}"
        lvl_info = levels_data.get(level_key, {})
        requires_approval = lvl_info.get("requires_approval", False)
        approved_by = lvl_info.get("approved_by", None)

        # Level 4 is ALWAYS restricted to human Owner
        if action_level == 4:
            return ActionCheckResult(
                allowed=False,
                permission_level=4,
                requires_approval=True,
                approved_by="owner",
                reason=f"Action '{action_name}' is Level 4 (Critical/Irreversible). Requires explicit Owner authorization."
            )

        # Level 3 actions require Director or explicit approval
        if action_level == 3:
            return ActionCheckResult(
                allowed=False,
                permission_level=3,
                requires_approval=True,
                approved_by="director",
                reason=f"Action '{action_name}' is Level 3 (External action). Requires Director sign-off."
            )

        # Check if agent has default clearance for action level (Level 1 or 2)
        if agent_max_level >= action_level:
            return ActionCheckResult(
                allowed=True,
                permission_level=action_level,
                requires_approval=False,
                approved_by=None,
                reason=f"Agent '{agent_name}' has Level {agent_max_level} clearance for Level {action_level} action."
            )

        # Agent lacks permission level
        return ActionCheckResult(
            allowed=False,
            permission_level=action_level,
            requires_approval=True,
            approved_by="director",
            reason=f"Agent '{agent_name}' has max Level {agent_max_level}, but action requires Level {action_level}."
        )

    def sanitize_prompt(self, text: str) -> str:
        """Strip or mask accidental credentials, tokens, or private secrets before LLM calls."""
        sensitive_patterns = [
            ("api_key", "sk-[a-zA-Z0-9_-]{20,}"),
            ("token", "bearer [a-zA-Z0-9_.-]{20,}"),
            ("password", r"password\s*=\s*['\"][^'\"]+['\"]"),
        ]
        import re
        sanitized = text
        for label, pat in sensitive_patterns:
            sanitized = re.sub(pat, f"[{label.upper()}_REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized


# Global instance
permission_engine = PermissionEngine()
