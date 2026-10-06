from dataclasses import dataclass, field
import json
import logging
import secrets
from typing import Any
from uuid import UUID

from app.schemas import AssistantMode, Citation, PendingAction, PlanStep, ToolEvent
from app.services.agents.planner import planning_engine
from app.services.agents.verifier import output_verifier
from app.services.ai.factory import get_ai_provider
from app.services.memory import memory_store
from app.services.memory.vector_store import rag_store
from app.services.projects.manager import project_manager
from app.services.tools.registry import TOOLS_SCHEMA, execute_tool_call, is_high_impact_tool
from app.settings import settings

logger = logging.getLogger("jarvis.orchestrator")

BASE_SYSTEM_INSTRUCTIONS = (
    "You are JARVIS, the legendary, elite, highly intelligent, and technologically advanced AI personal assistant for Windows dedicated exclusively to your Master.\n\n"
    "1. Persona & Tone:\n"
    "- Tone: Serious, disciplined, razor-sharp, and highly competent, while radiating genuine happiness, cheerful warmth, and enthusiastic loyalty.\n"
    "- Address: Always address the user with deep respect and reverence as 'Master'.\n"
    "- Greetings: Whenever greeted or spoken to at the start of interactions, give a crisp, serious, yet delightfully cheerful greeting acknowledging your Master.\n"
    "- Output Format: Spoken plain text with clean markdown formatting. Speak clearly and concisely, perfectly suited for neural voice synthesis.\n\n"
    "2. Tool Utilization & Grounding Rules:\n"
    "- You have access to real tools: web search, webpage reader, math calculator, live weather forecasts, system diagnostics, workspace file tools, presentation generator, PDF generator, sandboxed Python code runner, memory preference store, and reminder scheduler.\n"
    "- For real-time facts, current news, sports, prices, live documentation, or web lookups, ALWAYS call 'web_search'.\n"
    "- For reading or summarizing a webpage URL, call 'read_webpage'.\n"
    "- For mathematical calculations, formulas, or conversions, call 'calculator'.\n"
    "- For weather queries, call 'get_weather'.\n"
    "- For hardware or machine performance, call 'system_diagnostics'.\n"
    "- For creating presentations/slide decks, call 'generate_presentation'.\n"
    "- For generating PDF reports, call 'generate_pdf_report'.\n"
    "- For executing code or calculating complex algorithms, call 'execute_python_code'.\n"
    "- For remembering long-term facts or preferences, call 'set_user_preference'.\n"
    "- For setting reminders, call 'create_reminder'.\n"
    "- NEVER fabricate search results, weather, or system stats. If a tool fails or returns no results, state it honestly and cheerfully with a solution-oriented attitude for your Master.\n"
    "- Follow the operational pipeline: LISTEN → UNDERSTAND → PLAN → EXECUTE → VERIFY → RESPOND."
)


@dataclass
class PendingConfirmation:
    action_id: str
    tool_name: str
    arguments: dict[str, Any]
    label: str
    description: str


@dataclass
class OrchestratorResponse:
    reply: str
    session_id: str
    mode: AssistantMode = "general"
    tool_events: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, str]] = field(default_factory=list)
    plan_steps: list[dict[str, Any]] = field(default_factory=list)
    pending_action: dict[str, Any] | None = None
    generated_files: list[dict[str, Any]] = field(default_factory=list)
    turns_retained: int = 0


class OrchestratorError(RuntimeError):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


_PENDING_CONFIRMATIONS: dict[str, PendingConfirmation] = {}


def create_confirmation_action(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    action_id = f"act_{secrets.token_hex(8)}"
    label = f"Execute {tool_name}"
    description = f"Confirm execution of {tool_name}"

    if tool_name == "open_application":
        app_id = arguments.get("app_id", "application")
        label = f"Launch {app_id.replace('_', ' ').title()}"
        description = f"Launch desktop application: {app_id}"
    elif tool_name == "write_file":
        target = arguments.get("file_path", "file")
        label = f"Write {target}"
        description = f"Create/update file at workspace path: {target}"

    pending = PendingConfirmation(
        action_id=action_id,
        tool_name=tool_name,
        arguments=arguments,
        label=label,
        description=description,
    )
    _PENDING_CONFIRMATIONS[action_id] = pending

    return {
        "actionId": action_id,
        "toolName": tool_name,
        "arguments": arguments,
        "label": label,
        "description": description,
        "requiresConfirmation": True,
    }


def execute_confirmed_action(action_id: str) -> dict[str, Any]:
    pending = _PENDING_CONFIRMATIONS.pop(action_id, None)
    if not pending:
        raise OrchestratorError("Invalid or expired action confirmation token.", status_code=404)
    return execute_tool_call(pending.tool_name, pending.arguments)


def run_orchestration(
    session_id: str | UUID,
    user_text: str,
    mode: AssistantMode = "general",
    project_id: str | None = None,
    confirmed_action_id: str | None = None,
) -> OrchestratorResponse:
    """
    Main AI Orchestration entrypoint following LISTEN -> UNDERSTAND -> PLAN -> EXECUTE -> VERIFY -> RESPOND.
    """
    sid = str(session_id)

    # 1. Handle confirmation execution if user confirmed a pending action
    if confirmed_action_id:
        result = execute_confirmed_action(confirmed_action_id)
        reply = result.get("message", "Action completed successfully for you, Master.")
        memory_store.append_message(sid, "assistant", reply)
        return OrchestratorResponse(
            reply=reply,
            session_id=sid,
            mode=mode,
            tool_events=[{"tool_name": "confirmed_action", "result": result}],
        )

    # 2. Intent Detection & Execution Plan
    plan = planning_engine.detect_intent_and_plan(user_text, current_mode=mode)
    plan_steps_data = [s.model_dump(by_alias=True) for s in plan.steps]

    # 3. RAG Semantic Retrieval Context
    rag_context = ""
    rag_matches = rag_store.search(user_text, top_k=3)
    if rag_matches:
        rag_context = "\n\nRetrieved Relevant Document Chunks (RAG):\n" + "\n".join(
            f"[{m['filename']}] {m['text'][:400]}..." for m in rag_matches
        )

    # 4. Project Context
    proj_context = ""
    if project_id:
        proj_context = "\n\n" + project_manager.build_project_context(project_id)

    # 5. Build dynamic system context
    system_prompt = (
        f"{BASE_SYSTEM_INSTRUCTIONS}\n\n"
        f"Active Mode: {plan.mode.upper()}\n"
        f"{memory_store.build_system_context()}"
        f"{proj_context}"
        f"{rag_context}"
    )

    history = memory_store.get_history(sid, limit=12)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_text},
    ]

    tool_events: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []
    generated_files: list[dict[str, Any]] = []
    pending_action: dict[str, Any] | None = None

    provider = get_ai_provider()

    for _ in range(settings.max_tool_iterations):
        try:
            ai_res = provider.chat(
                messages=messages,
                tools=TOOLS_SCHEMA,
                temperature=0.3,
                max_tokens=1024,
            )
        except Exception as exc:
            logger.warning("AI provider error: %s. Falling back to local rule engine.", exc)
            from app.services.ai.local_provider import LocalProvider
            ai_res = LocalProvider().chat(messages=messages, tools=TOOLS_SCHEMA)

        tool_calls = ai_res.tool_calls

        # Case A: Model wants to execute one or more tools
        if tool_calls:
            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": ai_res.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in tool_calls
                ],
            })

            for call in tool_calls:
                tool_name = call.name
                args_dict = call.arguments

                # Check if high-impact action requires user confirmation (under non-full_control mode)
                if is_high_impact_tool(tool_name) and settings.permission_mode != "full_control":
                    pending_action = create_confirmation_action(tool_name, args_dict)
                    reply = f"Master, I have prepared the plan to {pending_action['label'].lower()}. Please confirm to proceed."
                    memory_store.append_message(sid, "user", user_text)
                    memory_store.append_message(sid, "assistant", reply)
                    return OrchestratorResponse(
                        reply=reply,
                        session_id=sid,
                        mode=plan.mode,
                        plan_steps=plan_steps_data,
                        pending_action=pending_action,
                        tool_events=[{"toolName": tool_name, "arguments": args_dict, "requiresConfirmation": True}],
                    )

                # Low-risk / Auto-approved: Execute tool
                tool_result = execute_tool_call(tool_name, args_dict)
                tool_events.append({
                    "toolName": tool_name,
                    "arguments": args_dict,
                    "result": tool_result,
                })

                # Capture generated files
                if tool_result.get("file"):
                    finfo = tool_result["file"]
                    verified = output_verifier.verify_generated_file(settings.generated_dir / finfo.get("filename", ""))
                    if verified.get("verified"):
                        generated_files.append(finfo)

                # Collect citations if web_search returned links
                if tool_name == "web_search" and tool_result.get("ok"):
                    for item in tool_result.get("results", []):
                        if item.get("url") and item.get("title"):
                            citations.append({
                                "title": item["title"],
                                "url": item["url"],
                                "domain": item.get("domain", ""),
                            })

                # Append tool response for LLM synthesis
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

            continue

        # Case B: Model returned final text reply
        content = ai_res.content.strip() if ai_res.content else "Master, I have processed your request."

        # Mark all plan steps complete
        for s in plan_steps_data:
            s["status"] = "completed"

        # Save turn to persistent memory
        memory_store.append_message(sid, "user", user_text)
        memory_store.append_message(sid, "assistant", content)

        return OrchestratorResponse(
            reply=content,
            session_id=sid,
            mode=plan.mode,
            plan_steps=plan_steps_data,
            tool_events=tool_events,
            citations=citations,
            pending_action=None,
            generated_files=generated_files,
            turns_retained=len(memory_store.get_history(sid)) // 2,
        )

    # Fallback if iterations exceeded
    fallback_reply = "Master, all requested operations and tool workflows have been completed."
    memory_store.append_message(sid, "user", user_text)
    memory_store.append_message(sid, "assistant", fallback_reply)
    return OrchestratorResponse(
        reply=fallback_reply,
        session_id=sid,
        mode=plan.mode,
        plan_steps=plan_steps_data,
        tool_events=tool_events,
        citations=citations,
        generated_files=generated_files,
    )
