from fastapi import APIRouter, Depends, HTTPException

from app.schemas import ResearchRequest, ResearchResponse
from app.services.auth import require_principal
from app.services.memory import memory_store
from app.services.research.researcher import perform_deep_research

router = APIRouter(prefix="/api/research", tags=["research"], dependencies=[Depends(require_principal)])


@router.post("/deep", response_model=ResearchResponse)
async def deep_research(
    request: ResearchRequest,
    owner_id: str = Depends(require_principal),
) -> ResearchResponse:
    try:
        result = perform_deep_research(
            query=request.query,
            depth=request.depth,
            generate_doc=request.generate_document,
        )
        if result.generated_file_url:
            memory_store.register_artifact(result.generated_file_url.rsplit("/", 1)[-1], owner_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Deep research failed: {exc}") from exc
