import concurrent.futures
import json
import logging
import secrets
import threading
import time
from typing import Any

from app.services.permissions import get_capability_for_tool
from app.services.coding.sandbox import execute_sandboxed_code
from app.services.document_generation.docx_generator import generate_docx_document
from app.services.document_generation.excel_generator import generate_excel_spreadsheet
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.document_generation.pptx_generator import generate_pptx_presentation
from app.services.local_actions import execute_local_action
from app.services.memory import memory_store
from app.services.research.researcher import perform_deep_research
from app.services.scheduler.reminder_service import reminder_service
from app.services.study_mode.notes_generator import generate_structured_study_notes
from app.services.tools.calculator import evaluate_expression
from app.services.tools.file_tools import read_workspace_file, search_workspace_files, write_workspace_file
from app.services.tools.system_info import get_system_diagnostics
from app.services.tools.weather import get_live_weather
from app.services.tools.web_reader import read_webpage_content
from app.services.tools.web_search import live_web_search

logger = logging.getLogger("jarvis.tools")
_idempotency_lock = threading.Lock()
_idempotency_results: dict[str, tuple[float, dict[str, Any]]] = {}
_IDEMPOTENCY_TTL_SECONDS = 600
_IDEMPOTENCY_CACHE_MAX_SIZE = 2048


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a live web search for current news, facts, products, prices, documentation, or real-time internet information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keywords"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Read and extract clean text content from a web page URL for analysis or summarization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The absolute HTTP or HTTPS URL to read"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Safely compute mathematical calculations, arithmetic, formulas, trigonometry, square roots, or conversions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression e.g. 'sqrt(256) * 14'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Fetch live real-time weather conditions, temperature, humidity, wind, and forecast for any city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or place name, e.g. 'Mumbai', 'London'"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_diagnostics",
            "description": "Get real hardware diagnostics: CPU usage %, RAM %, disk free space, OS version, machine uptime, and battery.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files and documents across the authorized user workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "File name substring or extension pattern"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read content from a workspace file (PDF, TXT, Code, Markdown, CSV, JSON).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative or absolute path within workspace"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or write content to a file in the user workspace. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Destination file path in workspace"},
                    "content": {"type": "string", "description": "The exact text or code content to write"},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Launch a Windows application on the user's desktop (Calculator, Notepad, File Explorer, VS Code). Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_id": {
                        "type": "string",
                        "enum": ["calculator", "notepad", "file_explorer", "vscode"],
                        "description": "The allowlisted application identifier",
                    },
                },
                "required": ["app_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_presentation",
            "description": "Generate a modern widescreen 16:9 PowerPoint (.pptx) presentation on any topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic or title of the presentation"},
                    "theme_color": {"type": "string", "enum": ["cyan", "gold", "emerald", "crimson", "purple"], "description": "Visual theme color"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pdf_report",
            "description": "Generate a publication-grade PDF report document with headings, tables, and styled formatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content_markdown": {"type": "string", "description": "Markdown formatted content for the report"},
                    "subtitle": {"type": "string", "description": "Optional subtitle"},
                },
                "required": ["title", "content_markdown"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Execute Python code in a safe, sandboxed subprocess and retrieve stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python source code to execute"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_preference",
            "description": "Save an important fact, user project preference, or instruction into long-term persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key, e.g. 'favorite_language', 'robotics_project_context'"},
                    "value": {"type": "string", "description": "The fact or preference details to remember"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_word_doc",
            "description": "Generate a professional Microsoft Word (.docx) document from markdown-formatted content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content_markdown": {"type": "string", "description": "Markdown formatted content"},
                    "subtitle": {"type": "string", "description": "Optional subtitle"},
                    "author": {"type": "string", "description": "Optional author name"},
                },
                "required": ["title", "content_markdown"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_web_research",
            "description": "Conduct comprehensive multi-source web research on any topic with live DuckDuckGo search, source scraping, and AI synthesis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research topic or question"},
                    "depth": {"type": "string", "enum": ["quick", "deep", "comprehensive"], "description": "Research depth"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a scheduled reminder for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Reminder text"},
                    "scheduled_time": {"type": "string", "description": "ISO time or descriptive time e.g. 'Tomorrow 8:00 AM'"},
                },
                "required": ["title", "scheduled_time"],
            },
        },
    },
]

for _tool_schema in TOOLS_SCHEMA:
    _tool_schema["function"]["parameters"]["additionalProperties"] = False

TOOL_SCHEMA_BY_NAME = {
    item["function"]["name"]: item["function"]["parameters"]
    for item in TOOLS_SCHEMA
}


def is_high_impact_tool(tool_name: str) -> bool:
    """Derive impact from the authoritative capability policy; unknown tools fail closed."""
    capability = get_capability_for_tool(tool_name)
    return (
        capability is None
        or capability.requires_confirmation
        or capability.is_destructive_or_sensitive
    )


def validate_tool_arguments(tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
    """Validate tool arguments against strict schema constraints."""
    if not isinstance(args, dict):
        return False, "Tool arguments must be a JSON dictionary."

    schema = TOOL_SCHEMA_BY_NAME.get(tool_name)
    if schema is None:
        return False, f"Tool '{tool_name}' is not registered."
    properties = schema.get("properties", {})
    unknown = set(args) - set(properties)
    if unknown:
        return False, f"Unexpected argument(s): {', '.join(sorted(unknown))}."
    missing = set(schema.get("required", [])) - set(args)
    if missing:
        return False, f"Missing required argument(s): {', '.join(sorted(missing))}."
    for name, value in args.items():
        definition = properties[name]
        expected_type = definition.get("type")
        if expected_type == "string" and not isinstance(value, str):
            return False, f"Argument '{name}' must be a string."
        if expected_type == "object" and not isinstance(value, dict):
            return False, f"Argument '{name}' must be an object."
        if "enum" in definition and value not in definition["enum"]:
            return False, f"Argument '{name}' must be one of: {', '.join(definition['enum'])}."

    if tool_name == "web_search":
        q = args.get("query")
        if not q or not isinstance(q, str) or not q.strip():
            return False, "Argument 'query' must be a non-empty string."

    elif tool_name == "read_webpage":
        u = args.get("url")
        if not u or not isinstance(u, str) or not u.strip():
            return False, "Argument 'url' must be a valid URL string."

    elif tool_name == "calculator":
        expr = args.get("expression")
        if not expr or not isinstance(expr, str) or not expr.strip():
            return False, "Argument 'expression' must be a non-empty mathematical expression string."

    elif tool_name == "get_weather":
        loc = args.get("location")
        if not loc or not isinstance(loc, str) or not loc.strip():
            return False, "Argument 'location' must be a non-empty location string."

    elif tool_name == "search_files":
        pat = args.get("pattern")
        if not isinstance(pat, str):
            return False, "Argument 'pattern' must be a search string."

    elif tool_name == "read_file":
        fp = args.get("file_path")
        if not fp or not isinstance(fp, str) or not fp.strip():
            return False, "Argument 'file_path' must be a valid file path string."

    elif tool_name == "write_file":
        fp = args.get("file_path")
        content = args.get("content")
        if not fp or not isinstance(fp, str) or not fp.strip():
            return False, "Argument 'file_path' must be a valid file path string."
        if content is None or not isinstance(content, str):
            return False, "Argument 'content' must be a string."

    elif tool_name == "open_application":
        app_id = args.get("app_id")
        allowed = {"calculator", "notepad", "file_explorer", "vscode"}
        if app_id not in allowed:
            return False, f"Argument 'app_id' must be one of: {', '.join(sorted(allowed))}."

    elif tool_name == "execute_python_code":
        code = args.get("code")
        if not code or not isinstance(code, str) or not code.strip():
            return False, "Argument 'code' must be a non-empty Python code string."

    elif tool_name == "set_user_preference":
        k = args.get("key")
        v = args.get("value")
        if not k or not isinstance(k, str) or not v or not isinstance(v, str):
            return False, "Arguments 'key' and 'value' must be non-empty strings."

    elif tool_name == "create_reminder":
        title = args.get("title")
        sch = args.get("scheduled_time")
        if not title or not isinstance(title, str) or not sch or not isinstance(sch, str):
            return False, "Arguments 'title' and 'scheduled_time' must be strings."

    elif tool_name == "generate_presentation":
        top = args.get("topic")
        if not top or not isinstance(top, str) or not top.strip():
            return False, "Argument 'topic' must be a non-empty string."

    elif tool_name == "generate_pdf_report":
        title = args.get("title")
        content = args.get("content_markdown")
        if not title or not isinstance(title, str) or not content or not isinstance(content, str):
            return False, "Arguments 'title' and 'content_markdown' must be strings."

    elif tool_name == "generate_word_doc":
        title = args.get("title")
        content = args.get("content_markdown")
        if not title or not isinstance(title, str) or not content or not isinstance(content, str):
            return False, "Arguments 'title' and 'content_markdown' must be strings."

    elif tool_name == "deep_web_research":
        q = args.get("query")
        if not q or not isinstance(q, str) or not q.strip():
            return False, "Argument 'query' must be a non-empty string."

    return True, ""


TOOL_TIMEOUTS: dict[str, float] = {
    "web_search": 20.0,
    "read_webpage": 20.0,
    "calculator": 5.0,
    "get_weather": 10.0,
    "system_diagnostics": 10.0,
    "search_files": 15.0,
    "read_file": 10.0,
    "write_file": 10.0,
    "open_application": 10.0,
    "generate_presentation": 30.0,
    "generate_pdf_report": 30.0,
    "execute_python_code": 20.0,
    "set_user_preference": 5.0,
    "create_reminder": 5.0,
    "generate_word_doc": 30.0,
    "deep_web_research": 45.0,
}
DEFAULT_TOOL_TIMEOUT: float = 20.0


def _dispatch_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute raw tool operation synchronously."""
    if tool_name == "web_search":
        return live_web_search(args.get("query", ""))

    if tool_name == "read_webpage":
        return read_webpage_content(args.get("url", ""))

    if tool_name == "calculator":
        return evaluate_expression(args.get("expression", ""))

    if tool_name == "get_weather":
        return get_live_weather(args.get("location", ""))

    if tool_name == "system_diagnostics":
        return get_system_diagnostics()

    if tool_name == "search_files":
        return search_workspace_files(args.get("pattern", ""))

    if tool_name == "read_file":
        return read_workspace_file(args.get("file_path", ""))

    if tool_name == "write_file":
        return write_workspace_file(args.get("file_path", ""), args.get("content", ""))

    if tool_name == "open_application":
        app_id = args.get("app_id")
        app = execute_local_action(app_id)  # type: ignore[arg-type]
        return {"ok": True, "app": app.label, "message": f"Opening {app.label}."}

    if tool_name == "generate_presentation":
        from app.services.agents.document_agent import document_agent
        res = document_agent.create_presentation_from_prompt(
            topic=args.get("topic", "Presentation"),
            theme_color=args.get("theme_color", "cyan"),
        )
        return {"ok": True, "file": res["file"], "message": f"PowerPoint '{res['file']['filename']}' generated successfully."}

    if tool_name == "generate_pdf_report":
        pdf_path = generate_pdf_document(
            title=args.get("title", "Report"),
            content_markdown=args.get("content_markdown", ""),
            subtitle=args.get("subtitle", ""),
        )
        return {
            "ok": True,
            "file": {
                "filename": pdf_path.name,
                "downloadUrl": f"/api/files/download/{pdf_path.name}",
                "sizeBytes": pdf_path.stat().st_size,
            },
            "message": f"PDF report '{pdf_path.name}' compiled successfully.",
        }

    if tool_name == "execute_python_code":
        res = execute_sandboxed_code(args.get("code", ""))
        return res.model_dump(by_alias=True)

    if tool_name == "set_user_preference":
        item_res = memory_store.set_memory(
            args.get("key", ""),
            args.get("value", ""),
            category="preference",
            provenance="user_directed_tool",
            source="user-directed memory tool",
        )
        item = item_res[0] if isinstance(item_res, tuple) else item_res
        return {"ok": True, "message": f"Remembered '{item.key}' in long-term memory."}

    if tool_name == "create_reminder":
        rem = reminder_service.add_reminder(args.get("title", ""), args.get("scheduled_time", ""))
        return {"ok": True, "reminder": rem.model_dump(by_alias=True), "message": f"Reminder '{rem.title}' scheduled for {rem.scheduled_time}."}

    if tool_name == "generate_word_doc":
        docx_path = generate_docx_document(
            title=args.get("title", "Document"),
            content_markdown=args.get("content_markdown", ""),
            subtitle=args.get("subtitle", ""),
            author=args.get("author", "JARVIS"),
        )
        return {
            "ok": True,
            "file": {
                "filename": docx_path.name,
                "downloadUrl": f"/api/files/download/{docx_path.name}",
                "sizeBytes": docx_path.stat().st_size,
            },
            "message": f"Word document '{docx_path.name}' generated successfully.",
        }

    if tool_name == "deep_web_research":
        research = perform_deep_research(
            query=args.get("query", ""),
            depth=args.get("depth", "deep"),
        )
        findings_text = getattr(research, "findings_markdown", getattr(research, "findingsMarkdown", ""))
        takeaways = getattr(research, "key_takeaways", getattr(research, "keyTakeaways", []))
        research_succeeded = research.status == "success"
        return {
            "ok": research_succeeded,
            "status": research.status,
            "synthesisStatus": research.synthesis_status,
            "sourceStatus": research.source_status,
            "topic": research.topic,
            "summary": research.summary,
            "findings": findings_text[:3000],
            "keyTakeaways": takeaways,
            "citations": [c.model_dump() for c in research.citations[:8]],
            "error": None if research_succeeded else research.diagnostic or "Research was incomplete.",
            "message": (
                f"Deep research on '{research.topic}' completed with {len(research.citations)} search result citations."
                if research_succeeded
                else research.diagnostic or "Deep research did not complete successfully."
            ),
        }

    return {"ok": False, "error": f"Tool '{tool_name}' is not recognized."}


def execute_tool_call(
    tool_name: str,
    raw_arguments: str | dict[str, Any],
    session_id: str = "general",
    timeout_seconds: float | None = None,
    execution_key: str | None = None,
) -> dict[str, Any]:
    """Execute a registered tool with strict schema validation, permission checks, timeouts, and error shielding."""
    from app.services.permissions import validate_tool_approval

    start_time = time.perf_counter()
    trace_id = f"tool_{secrets.token_hex(4)}"

    if isinstance(raw_arguments, str):
        try:
            args = json.loads(raw_arguments) if raw_arguments.strip() else {}
        except Exception:
            return {
                "ok": False,
                "tool": tool_name,
                "error": f"Invalid JSON arguments for tool '{tool_name}'.",
                "traceId": trace_id,
                "executionTimeMs": round((time.perf_counter() - start_time) * 1000, 2),
            }
    else:
        args = raw_arguments or {}

    # 1. Authoritative Permission Verification Immediately Before Execution
    is_approved, requires_confirm, perm_msg = validate_tool_approval(
        tool_name,
        arguments=args,
        session_id=session_id,
    )
    if not is_approved:
        return {
            "ok": False,
            "tool": tool_name,
            "error": perm_msg,
            "traceId": trace_id,
            "executionTimeMs": round((time.perf_counter() - start_time) * 1000, 2),
        }

    # 2. Strict Schema Validation
    is_valid, val_error = validate_tool_arguments(tool_name, args)
    if not is_valid:
        return {
            "ok": False,
            "tool": tool_name,
            "error": f"Schema validation error: {val_error}",
            "traceId": trace_id,
            "executionTimeMs": round((time.perf_counter() - start_time) * 1000, 2),
        }

    cache_key = f"{session_id}:{execution_key}" if execution_key else None
    if cache_key:
        with _idempotency_lock:
            now = time.monotonic()
            for old_key, (created, _) in list(_idempotency_results.items()):
                if now - created > _IDEMPOTENCY_TTL_SECONDS:
                    _idempotency_results.pop(old_key, None)
            previous = _idempotency_results.get(cache_key)
            if previous is not None:
                replay = dict(previous[1])
                replay["idempotentReplay"] = True
                return replay
            while len(_idempotency_results) >= _IDEMPOTENCY_CACHE_MAX_SIZE:
                removable = next(
                    (
                        key for key, (_, cached_result) in _idempotency_results.items()
                        if cached_result.get("executionStatus") != "in_progress"
                    ),
                    None,
                )
                if removable is None:
                    break
                _idempotency_results.pop(removable, None)
            _idempotency_results[cache_key] = (
                now,
                {
                    "ok": False,
                    "tool": tool_name,
                    "executionStatus": "in_progress",
                    "error": "Execution is already in progress; its side effect will not be repeated.",
                    "traceId": trace_id,
                },
            )

    timeout = timeout_seconds or TOOL_TIMEOUTS.get(tool_name, DEFAULT_TOOL_TIMEOUT)
    logger.info("Executing tool %s [trace=%s, timeout=%.1fs]", tool_name, trace_id, timeout)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_dispatch_tool, tool_name, args)
    try:
        raw_result = future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning("Tool %s timed out after %.1fs [trace=%s]", tool_name, timeout, trace_id)
        result = {
            "ok": False,
            "tool": tool_name,
            "executionStatus": "unknown",
            "error": f"Tool '{tool_name}' execution timed out after {timeout:.1f} seconds.",
            "traceId": trace_id,
            "executionTimeMs": duration_ms,
        }
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning("Tool %s execution failed: %s [trace=%s]", tool_name, exc, trace_id)
        result = {
            "ok": False,
            "tool": tool_name,
            "error": f"Tool execution failed: {exc}",
            "traceId": trace_id,
            "executionTimeMs": duration_ms,
        }
    else:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        if isinstance(raw_result, dict):
            raw_result.setdefault("tool", tool_name)
            raw_result.setdefault("traceId", trace_id)
            raw_result.setdefault("executionTimeMs", duration_ms)
            if raw_result.get("ok") is not True:
                has_explicit_status = "ok" in raw_result
                raw_result["ok"] = False
                if not raw_result.get("error"):
                    detail = raw_result.get("stderr") or raw_result.get("message")
                    raw_result["error"] = (
                        str(detail)
                        if detail
                        else "Tool reported failure."
                        if has_explicit_status
                        else "Tool returned no explicit success status."
                    )
            result = raw_result
        elif raw_result is None:
            result = {
                "ok": False,
                "tool": tool_name,
                "error": "Tool returned no result.",
                "traceId": trace_id,
                "executionTimeMs": duration_ms,
            }
        else:
            result = {
                "ok": True,
                "tool": tool_name,
                "result": raw_result,
                "traceId": trace_id,
                "executionTimeMs": duration_ms,
            }
    finally:
        # A timed-out callable may still be running; never block this request waiting for it.
        executor.shutdown(wait=False, cancel_futures=True)

    if cache_key:
        with _idempotency_lock:
            _idempotency_results[cache_key] = (time.monotonic(), dict(result))
    return result
