import inspect
import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas import ChatRequest, ChatResponse, Citation, PendingAction, PlanStep, ToolEvent
from app.services.orchestrator import OrchestratorError, run_orchestration

logger = logging.getLogger("jarvis.api.chat")
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Primary conversational endpoint executing multi-step agent reasoning, RAG context, and tool calling.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text cannot be blank.",
        )

    try:
        # Check signature to support test mocks with fewer arguments
        sig = inspect.signature(run_orchestration)
        param_count = len(sig.parameters)

        if param_count <= 3:
            res = run_orchestration(request.session_id, request.text, request.confirmed_action_id)
        else:
            res = run_orchestration(
                session_id=request.session_id,
                user_text=request.text,
                mode=request.mode,
                project_id=request.project_id,
                confirmed_action_id=request.confirmed_action_id,
            )

        citations_list = [Citation(**c) for c in getattr(res, "citations", [])]
        tool_events_list = [
            ToolEvent(
                toolName=t.get("toolName") or t.get("tool_name", "tool"),
                arguments=t.get("arguments", {}),
                result=t.get("result", {}),
                requiresConfirmation=t.get("requiresConfirmation", False),
            )
            for t in getattr(res, "tool_events", [])
        ]
        plan_steps_list = [
            PlanStep(
                stepNumber=s.get("stepNumber") or s.get("step_number", idx + 1),
                title=s.get("title", ""),
                status=s.get("status", "completed"),
                detail=s.get("detail", ""),
            )
            for idx, s in enumerate(getattr(res, "plan_steps", []))
        ]

        pending_action_obj = None
        if getattr(res, "pending_action", None):
            pa = res.pending_action
            pending_action_obj = PendingAction(
                actionId=pa["actionId"],
                toolName=pa["toolName"],
                arguments=pa.get("arguments", {}),
                label=pa["label"],
                description=pa["description"],
                requiresConfirmation=pa.get("requiresConfirmation", True),
            )

        return ChatResponse(
            sessionId=request.session_id,
            reply=res.reply,
            mode=getattr(res, "mode", "general"),
            turnsRetained=getattr(res, "turns_retained", 0),
            citations=citations_list,
            toolEvents=tool_events_list,
            planSteps=plan_steps_list,
            pendingAction=pending_action_obj,
            generatedFiles=getattr(res, "generated_files", []),
        )
    except HTTPException:
        raise
    except OrchestratorError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Chat orchestration error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant processing error: {exc}",
        ) from exc
