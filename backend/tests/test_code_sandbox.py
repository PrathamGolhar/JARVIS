from app.services.coding.sandbox import execute_sandboxed_code


def test_execute_python_code_success() -> None:
    code = "x = 10\ny = 25\nprint(f'SUM={x+y}')"
    res = execute_sandboxed_code(code=code, language="python")
    assert res.ok is True
    assert "SUM=35" in res.stdout
    assert res.exit_code == 0
    assert res.execution_time_ms >= 0


def test_execute_python_code_syntax_error() -> None:
    code = "def bad_func(\n"
    res = execute_sandboxed_code(code=code, language="python")
    assert res.ok is False
    assert res.exit_code != 0
    assert "SyntaxError" in res.stderr


def test_execute_python_code_timeout() -> None:
    code = "import time\ntime.sleep(5)\nprint('done')"
    res = execute_sandboxed_code(code=code, language="python", timeout_seconds=1)
    assert res.ok is False
    assert "timed out" in res.stderr
