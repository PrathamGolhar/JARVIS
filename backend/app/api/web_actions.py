from fastapi import APIRouter, HTTPException, status

from app.schemas import WebActionPlanRequest, WebActionPlanResponse
from app.services.web_action_planner import make_web_action_plan

router = APIRouter(prefix="/api/web-actions", tags=["web-actions"])


# ==============================================================================
# PHASE 4: THE HANDS (Safe Web Actions Route)
# ==============================================================================
@router.post("/plan", response_model=WebActionPlanResponse)
async def plan_web_action(request: WebActionPlanRequest) -> WebActionPlanResponse:
    """
    Return planned destination URL for frontend user confirmation.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text cannot be blank.",
        )

    plan = make_web_action_plan(request.text)
    return WebActionPlanResponse(
        kind=plan["kind"],
        label=plan["label"],
        url=plan["url"],
    )
