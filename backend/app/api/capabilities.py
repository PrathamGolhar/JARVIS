"""
API endpoints for JARVIS Approved Capabilities and Permissions Registry.
"""

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.permissions import (
    APPROVED_CAPABILITIES,
    ApprovalStatus,
    get_capability_status,
    is_capability_approved,
)

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


class CapabilityDto(BaseModel):
    name: str
    category: str
    description: str
    requiresConfirmation: bool
    toolName: str | None = None
    status: str


class CapabilityCheckRequest(BaseModel):
    capability: str


class CapabilityCheckResponse(BaseModel):
    capability: str
    approved: bool
    status: str
    requiresConfirmation: bool


@router.get("", response_model=list[CapabilityDto])
async def list_capabilities() -> list[CapabilityDto]:
    """List all registered and approved capabilities for JARVIS."""
    results: list[CapabilityDto] = []
    for cap in APPROVED_CAPABILITIES.values():
        status = ApprovalStatus.REQUIRES_CONFIRMATION if cap.requires_confirmation else ApprovalStatus.APPROVED
        results.append(
            CapabilityDto(
                name=cap.name,
                category=cap.category.value,
                description=cap.description,
                requiresConfirmation=cap.requires_confirmation,
                toolName=cap.tool_name,
                status=status.value,
            )
        )
    return results


@router.post("/check", response_model=CapabilityCheckResponse)
async def check_capability(req: CapabilityCheckRequest) -> CapabilityCheckResponse:
    """Check if a specific capability is approved and if it requires confirmation."""
    cap_name = req.capability.strip()
    approved = is_capability_approved(cap_name)
    status = get_capability_status(cap_name)
    cap = APPROVED_CAPABILITIES.get(cap_name)
    requires_conf = cap.requires_confirmation if cap else False

    return CapabilityCheckResponse(
        capability=cap_name,
        approved=approved,
        status=status.value,
        requiresConfirmation=requires_conf,
    )
