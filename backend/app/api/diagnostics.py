from fastapi import APIRouter

from app.schemas import DiagnosticsResponse
from app.services.diagnostics_service import get_deep_diagnostics

router = APIRouter(prefix="/api", tags=["diagnostics"])


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics() -> DiagnosticsResponse:
    """
    Return truthful, measured diagnostics across all backend subsystems.
    """
    return get_deep_diagnostics()
