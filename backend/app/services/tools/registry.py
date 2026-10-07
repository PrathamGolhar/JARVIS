from enum import Enum
import json
import logging
from typing import Any

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


class RiskLevel(str, Enum):
    LOW = "low"  # Auto-executable
    HIGH = "high"  # Requires explicit confirmation


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

TOOL_RISK_MAP = {
    "web_search": RiskLevel.LOW,
    "read_webpage": RiskLevel.LOW,
    "calculator": RiskLevel.LOW,
    "get_weather": RiskLevel.LOW,
    "system_diagnostics": RiskLevel.LOW,
    "search_files": RiskLevel.LOW,
    "read_file": RiskLevel.LOW,
    "generate_presentation": RiskLevel.LOW,
    "generate_pdf_report": RiskLevel.LOW,
    "generate_word_doc": RiskLevel.LOW,
    "deep_web_research": RiskLevel.LOW,
    "execute_python_code": RiskLevel.LOW,
    "set_user_preference": RiskLevel.LOW,
    "create_reminder": RiskLevel.LOW,
    "write_file": RiskLevel.HIGH,
    "open_application": RiskLevel.HIGH,
}


def is_high_impact_tool(tool_name: str) -> bool:
    return TOOL_RISK_MAP.get(tool_name, RiskLevel.LOW) == RiskLevel.HIGH


def execute_tool_call(tool_name: str, raw_arguments: str | dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool with parsed arguments and error shielding."""
    if isinstance(raw_arguments, str):
        try:
            args = json.loads(raw_arguments) if raw_arguments.strip() else {}
        except Exception:
            args = {}
    else:
        args = raw_arguments or {}

    try:
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
            return {"ok": True, "app": app.label, "message": f"Opening {app.label} for you, Master."}

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
            item = memory_store.set_memory(args.get("key", ""), args.get("value", ""))
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
            return {
                "ok": True,
                "topic": research.topic,
                "summary": research.summary,
                "findings": research.findingsMarkdown[:3000],
                "keyTakeaways": research.keyTakeaways,
                "citations": [c.model_dump() for c in research.citations[:8]],
                "message": f"Deep research on '{research.topic}' completed with {len(research.citations)} verified sources.",
            }

        return {"ok": False, "error": f"Tool '{tool_name}' is not recognized."}
    except Exception as exc:
        logger.warning("Tool %s execution failed: %s", tool_name, exc)
        return {"ok": False, "tool": tool_name, "error": f"Tool execution failed: {exc}"}
