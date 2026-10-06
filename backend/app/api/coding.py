from fastapi import APIRouter, HTTPException

from app.schemas import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeExecutionRequest,
    CodeExecutionResponse,
)
from app.services.coding.assistant import analyze_code_task
from app.services.coding.sandbox import execute_sandboxed_code

router = APIRouter(prefix="/api/code", tags=["coding"])


@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest) -> CodeExecutionResponse:
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
