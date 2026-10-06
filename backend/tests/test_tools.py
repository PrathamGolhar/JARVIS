from app.services.tools.calculator import evaluate_expression
from app.services.tools.file_tools import read_workspace_file, search_workspace_files, write_workspace_file
from app.services.tools.registry import execute_tool_call, is_high_impact_tool
from app.services.tools.system_info import get_system_diagnostics
from app.services.tools.weather import get_live_weather
from app.services.tools.web_reader import read_webpage_content
from app.services.tools.web_search import live_web_search


def test_calculator_arithmetic_and_functions() -> None:
    res = evaluate_expression("45 * 2 + sqrt(144)")
    assert res["ok"] is True
    assert res["result"] == 102

    res2 = evaluate_expression("sin(0) + cos(0) * 10")
    assert res2["ok"] is True
    assert res2["result"] == 10

    res_err = evaluate_expression("import os; os.system('calc')")
    assert res_err["ok"] is False


def test_system_diagnostics_metrics() -> None:
    diagnostics = get_system_diagnostics()
    assert diagnostics["ok"] is True
    assert "cpu_usage_percent" in diagnostics
    assert "ram_usage_percent" in diagnostics
    assert "disk_usage_percent" in diagnostics
    assert "os" in diagnostics


def test_tool_registry_risk_mapping() -> None:
    assert is_high_impact_tool("open_application") is True
    assert is_high_impact_tool("write_file") is True
    assert is_high_impact_tool("calculator") is False
    assert is_high_impact_tool("web_search") is False
    assert is_high_impact_tool("get_weather") is False


def test_file_tools_workspace_confinement() -> None:
    # Safe write & read in test workspace
    write_res = write_workspace_file("test_artifact.txt", "Jarvis active")
    assert write_res["ok"] is True

    read_res = read_workspace_file("test_artifact.txt")
    assert read_res["ok"] is True
    assert "Jarvis active" in read_res["content"]

    search_res = search_workspace_files("test_artifact")
    assert search_res["ok"] is True
    assert len(search_res["files"]) >= 1

    # Security check: Prevent path traversal
    escape_res = read_workspace_file("../../escaped_file.txt")
    assert escape_res["ok"] is False
    assert "outside the authorized workspace" in escape_res["error"]


def test_web_reader_ssrf_protection() -> None:
    res = read_webpage_content("http://127.0.0.1:8080/admin")
    assert res["ok"] is False
    assert "restricted" in res["error"]

    res_bad = read_webpage_content("ftp://example.com/file")
    assert res_bad["ok"] is False
    assert "Invalid URL scheme" in res_bad["error"]
