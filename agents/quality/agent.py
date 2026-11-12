"""Specialized Quality & Security Autonomous Agent."""

import logging
from typing import Dict, Any
from agents.base import BaseAgent
from tool_factory.sandbox import ASTSecurityScanner

logger = logging.getLogger("ai_company.agent.quality")


class QualitySecurityAgent(BaseAgent):
    """Enforces enterprise security, runs static code audits, and validates tool deployments."""

    def __init__(self):
        super().__init__(
            name="quality",
            role="Chief Quality & Security Officer",
            description="Audits code, enforces permission boundaries, verifies tests, and guards system security.",
            max_permission_level=2
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security/quality audit task."""
        inputs = task.get("inputs", {})
        code_to_audit = inputs.get("code")

        audit_results = {}
        if code_to_audit:
            is_safe, violations = ASTSecurityScanner.scan(code_to_audit)
            audit_results = {
                "ast_safe": is_safe,
                "violations": violations,
                "verdict": "PASSED" if is_safe else "REJECTED"
            }

        result = await super().execute_task(task)
        if audit_results:
            result["security_audit"] = audit_results

        # Save audit report to workspace
        audit_fn = f"security_audit_{task.get('id', 'latest')}.md"
        audit_md = (
            f"# Security Audit Report: {task.get('title')}\n\n"
            f"Verdict: {audit_results.get('verdict', 'PASSED')}\n"
            f"Violations: {audit_results.get('violations', [])}\n\n"
            f"{result.get('summary', '')}\n"
        )
        try:
            self.write_workspace_file(audit_fn, audit_md)
            result["saved_audit_report"] = audit_fn
            result["saved_audit"] = audit_fn
            result["saved_file"] = audit_fn
        except Exception as e:
            logger.warning(f"Could not save audit report: {e}")

        return result
