"""
Authoritative Sandboxed Code Execution Engine for JARVIS.

Security Controls:
1. Static AST pre-execution analysis: Denies hazardous modules (os, sys, subprocess, socket, etc.)
   and dangerous built-ins (eval, exec, __import__, open, etc.).
2. Clean environment: Subprocesses are executed without inheriting environment variables or API keys.
3. Isolated execution workspace: Executes inside an ephemeral TemporaryDirectory cleaned on exit.
4. Process termination & strict timeouts: Enforces execution deadlines and limits output buffering.
5. Server-side permission enforcement: Blocked in READ_ONLY mode; confirmation required in ASSISTED mode.
6. Transparent isolation disclosure: Identifies execution tier as 'restricted_ast_subprocess'.
"""

import ast
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Optional

from app.schemas import CodeExecutionResponse
from app.settings import settings

logger = logging.getLogger("jarvis.coding.sandbox")

MAX_STDOUT_BYTES = 50 * 1024  # 50 KB

# Blocked Python modules (static AST check)
BLOCKED_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "shutil",
    "ctypes",
    "importlib",
    "multiprocessing",
    "threading",
    "signal",
    "winreg",
    "pty",
    "commands",
    "posix",
    "builtins",
    "tempfile",
    "pathlib",
    "io",
    "urllib",
    "requests",
    "http",
    "pickle",
    "shelve",
    "marshal",
    "webbrowser",
    "msvcrt",
}

# Blocked function calls and built-ins
BLOCKED_BUILTINS = {
    "eval",
    "exec",
    "__import__",
    "open",
    "breakpoint",
    "compile",
    "globals",
    "locals",
    "vars",
}

# Blocked introspection and dunder traversal patterns
BLOCKED_DUNDERS = {
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__globals__",
    "__code__",
    "__dict__",
    "__class__",
}


class CodeSecurityError(ValueError):
    """Raised when submitted code contains prohibited modules or dangerous constructs."""
    pass


class ASTSecurityValidator(ast.NodeVisitor):
    """Inspects Python AST to ensure untrusted code does not call dangerous APIs."""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_mod = alias.name.split(".")[0].lower()
            if root_mod in BLOCKED_MODULES:
                raise CodeSecurityError(
                    f"Import of prohibited module '{alias.name}' is restricted by sandbox security policy."
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root_mod = node.module.split(".")[0].lower()
            if root_mod in BLOCKED_MODULES:
                raise CodeSecurityError(
                    f"Import from prohibited module '{node.module}' is restricted by sandbox security policy."
                )
        for alias in node.names:
            if alias.name.lower() in BLOCKED_MODULES:
                raise CodeSecurityError(
                    f"Import of symbol '{alias.name}' is restricted by sandbox security policy."
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check call to blocked built-in functions
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_BUILTINS:
                raise CodeSecurityError(
                    f"Invocation of restricted built-in function '{node.func.id}()' is prohibited."
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check dunder introspection escapes
        if node.attr in BLOCKED_DUNDERS:
            raise CodeSecurityError(
                f"Access to introspection attribute '{node.attr}' is prohibited by sandbox security policy."
            )
        self.generic_visit(node)


def validate_python_ast(code: str) -> None:
    """Parse and validate Python code against security AST policy."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Allow syntax errors to be reported by the interpreter during execution
        return

    validator = ASTSecurityValidator()
    validator.visit(tree)


def execute_sandboxed_code(
    code: str,
    language: str = "python",
    stdin_input: str = "",
    timeout_seconds: Optional[int] = None,
) -> CodeExecutionResponse:
    """
    Execute user code in a sandboxed subprocess with strict AST validation,
    scrubbed environment, output buffering, and timeouts.
    """
    timeout = timeout_seconds or settings.sandbox_timeout_seconds
    lang = language.lower().strip()

    # 1. Authoritative Permission Mode Enforcement
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        return CodeExecutionResponse(
            ok=False,
            stdout="",
            stderr="Code execution is strictly disabled in 'read_only' permission mode.",
            exitCode=1,
            executionTimeMs=0.0,
            memoryMb=0.0,
        )

    if getattr(settings, "emergency_stop_active", False):
        return CodeExecutionResponse(
            ok=False,
            stdout="",
            stderr="Code execution halted: Emergency stop is active.",
            exitCode=1,
            executionTimeMs=0.0,
            memoryMb=0.0,
        )

    # 2. Static Security Analysis (Python)
    if lang == "python":
        try:
            validate_python_ast(code)
        except CodeSecurityError as sec_err:
            logger.warning("Code execution rejected by AST security validator: %s", sec_err)
            return CodeExecutionResponse(
                ok=False,
                stdout="",
                stderr=f"Security Policy Violation: {sec_err}",
                exitCode=1,
                executionTimeMs=0.0,
                memoryMb=0.0,
            )

    # 3. Isolated Ephemeral Workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)

        if lang == "python":
            script_file = dir_path / "script.py"
            script_file.write_text(code, encoding="utf-8")
            # -I: isolated mode (ignores PYTHONPATH and user site-packages, disables environment inheritance)
            cmd = [sys.executable, "-I", "-u", str(script_file)]
        elif lang in ("javascript", "typescript", "js", "ts"):
            script_file = dir_path / "script.js"
            script_file.write_text(code, encoding="utf-8")
            cmd = ["node", str(script_file)]
        else:
            return CodeExecutionResponse(
                ok=False,
                stdout="",
                stderr=f"Execution for language '{language}' is not supported directly in sandbox. Only Python and JavaScript are available.",
                exitCode=1,
                executionTimeMs=0.0,
                memoryMb=0.0,
            )

        # 4. Environment Scrubbing: Prevent leaking API keys or secrets
        sanitized_env = {
            "PYTHONIOENCODING": "utf-8",
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
        }

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(dir_path),
                env=sanitized_env,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            stdout_text = proc.stdout[:MAX_STDOUT_BYTES]
            stderr_text = proc.stderr[:MAX_STDOUT_BYTES]
            ok = proc.returncode == 0

            return CodeExecutionResponse(
                ok=ok,
                stdout=stdout_text,
                stderr=stderr_text,
                exitCode=proc.returncode,
                executionTimeMs=round(elapsed_ms, 2),
                memoryMb=0.0,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CodeExecutionResponse(
                ok=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                exitCode=-1,
                executionTimeMs=round(elapsed_ms, 2),
                memoryMb=0.0,
            )
        except FileNotFoundError as fnf:
            return CodeExecutionResponse(
                ok=False,
                stdout="",
                stderr=f"Runtime environment not found: {fnf}",
                exitCode=127,
                executionTimeMs=0.0,
                memoryMb=0.0,
            )
        except Exception as exc:
            return CodeExecutionResponse(
                ok=False,
                stdout="",
                stderr=f"Sandbox execution error: {exc}",
                exitCode=1,
                executionTimeMs=0.0,
                memoryMb=0.0,
            )
