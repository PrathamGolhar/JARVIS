import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.schemas import ChatRequest, ChatResponse, Citation, PendingAction, PlanStep, ToolEvent
from app.services.auth import require_auth, require_principal
from app.services.memory import memory_store
from app.services.projects.manager import project_manager
from app.services.orchestrator import OrchestratorError, run_orchestration_async

logger = logging.getLogger("jarvis.api.chat")
router = APIRouter(prefix="/api", tags=["chat"], dependencies=[Depends(require_auth)])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    owner_id: str = Depends(require_principal),
) -> ChatResponse:
    """
    Primary conversational endpoint executing multi-step agent reasoning, RAG context, and tool calling.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text cannot be blank.",
        )
    effective_idempotency_key = request.idempotency_key or idempotency_key
    if effective_idempotency_key and (not effective_idempotency_key.strip() or len(effective_idempotency_key) > 128):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Idempotency-Key must contain 1 to 128 non-whitespace characters.",
        )

    if request.project_id and not project_manager.get_project(request.project_id, owner_id=owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if not memory_store.ensure_session_owner(request.session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")

    try:
        res = await run_orchestration_async(
            session_id=request.session_id,
            user_text=request.text,
            mode=request.mode,
            response_style=request.response_style,
            project_id=request.project_id,
            confirmed_action_id=request.confirmed_action_id,
            image_ids=request.image_ids,
            provider_override=request.provider_override,
            idempotency_key=effective_idempotency_key,
            owner_id=owner_id,
        )

        citations_list = [Citation(**c) for c in getattr(res, "citations", [])]
        tool_events_list = [
            ToolEvent(
                toolName=t.get("toolName") or t.get("tool_name", "tool"),
                arguments=t.get("arguments", {}),
                result=t.get("result", {}),
                requiresConfirmation=t.get("requiresConfirmation", False),
                status=t.get("status"),
                fileVerification=t.get("fileVerification"),
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
            executionStatus=getattr(res, "execution_status", "unverified"),
            verification=getattr(res, "verification", {}),
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
