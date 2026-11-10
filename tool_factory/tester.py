"""Automated Test Runner for Tool Factory."""

import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from tool_factory.sandbox import tool_sandbox

logger = logging.getLogger("ai_company.tool_tester")


class TestReport(BaseModel):
    passed: bool
    runtime_seconds: float
    stdout: str
    stderr: str
    violations: List[str] = []
    error: Optional[str] = None


class ToolTester:
    """Executes unit tests and checks behavioral specifications in isolation."""

    def __init__(self, sandbox=None):
        self.sandbox = sandbox or tool_sandbox

    async def run_tests(
        self,
        tool_code: str,
        test_code: str,
        timeout: int = 15
    ) -> TestReport:
        """Run tests against candidate tool code."""
        start_time = time.time()
        result = await self.sandbox.execute_in_sandbox(
            code_str=tool_code,
            test_str=test_code,
            timeout=timeout
        )
        duration = round(time.time() - start_time, 3)

        return TestReport(
            passed=result.get("success", False),
            runtime_seconds=duration,
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            violations=result.get("violations", []),
            error=result.get("error")
        )


# Global tester singleton
tool_tester = ToolTester()
