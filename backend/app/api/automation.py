from fastapi import APIRouter, HTTPException

from app.schemas import ReminderCreateRequest, ReminderItem
from app.services.scheduler.reminder_service import reminder_service

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.get("/reminders", response_model=list[ReminderItem])
async def list_reminders() -> list[ReminderItem]:
    return reminder_service.list_reminders()


@router.post("/reminders", response_model=ReminderItem)
async def create_reminder(request: ReminderCreateRequest) -> ReminderItem:
    if not request.title.strip():
        raise HTTPException(status_code=422, detail="Title cannot be blank.")
    return reminder_service.add_reminder(
        title=request.title,
        scheduled_time=request.scheduled_time,
        recurring=request.recurring,
    )


@router.patch("/reminders/{reminder_id}/toggle", response_model=ReminderItem)
async def toggle_reminder(reminder_id: str) -> ReminderItem:
    item = reminder_service.toggle_reminder(reminder_id)
    if not item:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return item


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    ok = reminder_service.delete_reminder(reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"ok": True, "message": "Reminder deleted successfully."}
