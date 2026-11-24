from fastapi import APIRouter, Depends

from app.schemas import DiagnosticsResponse
from app.services.auth import require_auth
from app.services.diagnostics_service import get_deep_diagnostics

router = APIRouter(prefix="/api", tags=["diagnostics"], dependencies=[Depends(require_auth)])


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics() -> DiagnosticsResponse:
    """
    Return truthful, measured diagnostics across all backend subsystems.
    """
    return get_deep_diagnostics()
