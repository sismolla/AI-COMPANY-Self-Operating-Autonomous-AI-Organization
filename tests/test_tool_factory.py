"""Tests for Self-Building Tool Factory Subsystem."""

import pytest
from tool_factory.sandbox import ASTSecurityScanner, ToolSandbox
from tool_factory.tester import ToolTester
from tool_factory.registry import ToolRegistry
from tool_factory.builder import ToolBuilder


def test_ast_security_scanner():
    safe_code = """
import math
import re

def calculate_stats(numbers):
    return {"mean": sum(numbers) / len(numbers), "sqrt_sum": math.sqrt(sum(numbers))}
"""
    is_safe, violations = ASTSecurityScanner.scan(safe_code)
    assert is_safe is True
    assert len(violations) == 0

    unsafe_code = """
import subprocess

def run_danger():
    subprocess.call(["ls", "-la"])
"""
    is_safe, violations = ASTSecurityScanner.scan(unsafe_code)
    assert is_safe is False
    assert any("subprocess" in v for v in violations)


def test_ast_forbidden_calls():
    bad_call = """
import os
def rm():
    os.system("echo hacked")
"""
    is_safe, violations = ASTSecurityScanner.scan(bad_call)
    assert is_safe is False
    assert any("os.system" in v or "system" in v for v in violations)


@pytest.mark.asyncio
async def test_tool_sandbox_execution(tmp_path):
    sandbox = ToolSandbox(base_dir=tmp_path / "sandbox")
    code = "def add(a, b): return a + b\n"
    test_code = "from tool import add\nassert add(2, 3) == 5\n"

    result = await sandbox.execute_in_sandbox(code, test_code)
    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.asyncio
async def test_tool_tester(tmp_path):
    sandbox = ToolSandbox(base_dir=tmp_path / "sandbox")
    tester = ToolTester(sandbox=sandbox)

    code = "def multiply(x, y): return x * y\n"
    test_code = "from tool import multiply\nassert multiply(3, 4) == 12\n"

    report = await tester.run_tests(code, test_code)
    assert report.passed is True
    assert report.runtime_seconds >= 0


@pytest.mark.asyncio
async def test_tool_registry_and_execution(tmp_path):
    registry = ToolRegistry(tools_dir=tmp_path / "tools")
    code = "def greet(name: str) -> str: return f'Hello {name}'\n"
    test_code = "from tool import greet\nassert greet('World') == 'Hello World'\n"

    await registry.register_tool(
        name="greeter",
        code=code,
        test_code=test_code,
        description="Greets user",
        permission_level=1
    )

    # Execute tool function as an agent with Level 2 clearance
    exec_res = await registry.execute_tool(
        tool_name="greeter",
        function_name="greet",
        calling_agent="engineering",
        name="Antigravity"
    )
    assert exec_res["success"] is True
    assert exec_res["result"] == "Hello Antigravity"
