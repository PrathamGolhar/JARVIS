from fastapi import APIRouter, HTTPException

from app.schemas import ResearchRequest, ResearchResponse
from app.services.research.researcher import perform_deep_research

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/deep", response_model=ResearchResponse)
async def deep_research(request: ResearchRequest) -> ResearchResponse:
    try:
        return perform_deep_research(
            query=request.query,
            depth=request.depth,
            generate_doc=request.generate_document,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Deep research failed: {exc}") from exc
