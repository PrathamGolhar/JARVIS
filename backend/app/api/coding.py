from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeExecutionRequest,
    CodeExecutionResponse,
)
from app.services.auth import require_auth
from app.services.coding.assistant import analyze_code_task
from app.services.coding.sandbox import execute_sandboxed_code
from app.settings import settings

router = APIRouter(prefix="/api/code", tags=["coding"], dependencies=[Depends(require_auth)])


@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest) -> CodeExecutionResponse:
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct code execution is disabled in 'read_only' permission mode.",
        )

    try:
        return execute_sandboxed_code(
            code=request.code,
            language=request.language,
            stdin_input=request.stdin_input,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Code execution error: {exc}") from exc


@router.post("/analyze", response_model=CodeAnalysisResponse)
async def analyze_code(request: CodeAnalysisRequest) -> CodeAnalysisResponse:
    try:
        return analyze_code_task(
            code=request.code,
            language=request.language,
            task=request.task,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Code analysis error: {exc}") from exc
