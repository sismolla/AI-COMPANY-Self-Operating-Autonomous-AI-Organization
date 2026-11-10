"""Isolated Sandbox and AST Security Scanner for Tool Factory."""

import ast
import os
import sys
import uuid
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from config.settings import settings


class SecurityViolation(Exception):
    """Raised when unsafe code patterns or unauthorized APIs are detected."""
    pass


class ASTSecurityScanner:
    """Analyzes Python code AST to prevent dangerous system calls and escapes."""

    # Disallowed modules for untrusted agent-built tools
    FORBIDDEN_MODULES = {
        "subprocess", "shutil", "posix", "ctypes", "winreg",
        "multiprocessing", "pty", "socketserver", "paramiko"
    }

    # Disallowed builtins / functions
    FORBIDDEN_CALLS = {
        "eval", "exec", "__import__", "globals", "locals"
    }

    @classmethod
    def scan(cls, code_str: str) -> Tuple[bool, List[str]]:
        """Static AST scan of tool code. Returns (is_safe, list_of_violations)."""
        violations = []
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, [f"SyntaxError in code: {e}"]

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES:
                        violations.append(f"Forbidden module import: '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES:
                        violations.append(f"Forbidden module import from: '{node.module}'")

            # Check calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.FORBIDDEN_CALLS:
                        violations.append(f"Forbidden builtin call: '{node.func.id}()'")
                elif isinstance(node.func, ast.Attribute):
                    # Check os.system, os.popen, etc.
                    if node.func.attr in {"system", "popen", "spawn", "fork", "kill", "remove", "unlink"}:
                        violations.append(f"Forbidden system call: '{node.func.attr}()'")

        return len(violations) == 0, violations


class ToolSandbox:
    """Provides isolated temp workspace and subprocess execution for testing tools."""

    def __init__(self, base_dir: Path = settings.WORKSPACE_DIR / "sandbox"):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def execute_in_sandbox(
        self,
        code_str: str,
        test_str: Optional[str] = None,
        timeout: int = settings.SANDBOX_TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """Execute Python code in isolated workspace subprocess with timeout."""
        session_id = uuid.uuid4().hex[:8]
        session_dir = self.base_dir / f"sandbox_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        # 1. AST Security Scan
        is_safe, violations = ASTSecurityScanner.scan(code_str)
        if not is_safe:
            shutil.rmtree(session_dir, ignore_errors=True)
            return {
                "success": False,
                "error": "AST Security Scan Failed",
                "violations": violations,
                "stdout": "",
                "stderr": "\n".join(violations)
            }

        if test_str:
            is_test_safe, test_violations = ASTSecurityScanner.scan(test_str)
            if not is_test_safe:
                shutil.rmtree(session_dir, ignore_errors=True)
                return {
                    "success": False,
                    "error": "Test AST Security Scan Failed",
                    "violations": test_violations,
                    "stdout": "",
                    "stderr": "\n".join(test_violations)
                }

        # 2. Write code files
        tool_file = session_dir / "tool.py"
        with open(tool_file, "w", encoding="utf-8") as f:
            f.write(code_str)

        runner_file = session_dir / "run_test.py"
        test_content = (
            "import sys\nfrom tool import *\n\n"
            + (test_str if test_str else "print('Tool syntax and import verified.')\n")
            + "\nprint('TESTS_COMPLETED_SUCCESSFULLY')\n"
        )
        with open(runner_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        # 3. Execute in subprocess
        try:
            cmd = [sys.executable, str(runner_file)]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(session_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    "PYTHONPATH": str(session_dir),
                    "PATH": os.environ.get("PATH", ""),
                    "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")
                }
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(timeout)
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            passed = (proc.returncode == 0) and ("TESTS_COMPLETED_SUCCESSFULLY" in stdout)

            return {
                "success": passed,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "violations": []
            }

        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Execution timed out after {timeout} seconds.",
                "stdout": "",
                "stderr": "Timeout expired.",
                "violations": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "violations": []
            }
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)


# Global sandbox singleton
tool_sandbox = ToolSandbox()
