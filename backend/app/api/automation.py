from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import ReminderCreateRequest, ReminderItem
from app.services.auth import require_auth
from app.services.scheduler.reminder_service import reminder_service
from app.settings import settings

router = APIRouter(prefix="/api/automation", tags=["automation"], dependencies=[Depends(require_auth)])


def check_write_permission() -> None:
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Automation and reminder modifications are disabled in 'read_only' permission mode.",
        )


@router.get("/reminders", response_model=list[ReminderItem])
async def list_reminders() -> list[ReminderItem]:
    return reminder_service.list_reminders()


@router.post("/reminders", response_model=ReminderItem)
async def create_reminder(request: ReminderCreateRequest) -> ReminderItem:
    check_write_permission()
    if not request.title.strip():
        raise HTTPException(status_code=422, detail="Title cannot be blank.")
    return reminder_service.add_reminder(
        title=request.title,
        scheduled_time=request.scheduled_time,
        recurring=request.recurring,
    )


@router.patch("/reminders/{reminder_id}/toggle", response_model=ReminderItem)
async def toggle_reminder(reminder_id: str) -> ReminderItem:
    check_write_permission()
    item = reminder_service.toggle_reminder(reminder_id)
    if not item:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return item


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    check_write_permission()
    ok = reminder_service.delete_reminder(reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"ok": True, "message": "Reminder deleted successfully."}
