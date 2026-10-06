import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from app.schemas import CodeExecutionResponse
from app.settings import settings

MAX_STDOUT_BYTES = 50 * 1024  # 50 KB


def execute_sandboxed_code(
    code: str,
    language: str = "python",
    stdin_input: str = "",
    timeout_seconds: int | None = None,
) -> CodeExecutionResponse:
    """
    Execute user code in a sandboxed subprocess with strict timeouts and output buffering.
    Supported: Python (and NodeJS if available on host).
    """
    timeout = timeout_seconds or settings.sandbox_timeout_seconds
    lang = language.lower().strip()

    with tempfile.TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)

        if lang == "python":
            script_file = dir_path / "script.py"
            script_file.write_text(code, encoding="utf-8")
            cmd = [sys.executable, "-u", str(script_file)]
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

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(dir_path),
                env={"PYTHONIOENCODING": "utf-8", "PATH": os.environ.get("PATH", "")},
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            stdout_text = proc.stdout[:MAX_STDOUT_BYTES]
            stderr_text = proc.stderr[:MAX_STDOUT_BYTES]
            ok = (proc.returncode == 0)

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
