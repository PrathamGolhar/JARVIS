from datetime import datetime
import json
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.schemas import ReminderItem
from app.settings import settings


class ReminderService:
    """
    Background reminder and scheduled task management system.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_file = storage_path or (settings.data_dir / "reminders.json")
        self._lock = RLock()
        self._init_storage()

    def _init_storage(self) -> None:
        with self._lock:
            if not self.storage_file.exists():
                self.storage_file.write_text("[]", encoding="utf-8")

    def list_reminders(self) -> list[ReminderItem]:
        with self._lock:
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                return [
                    ReminderItem(
                        id=r["id"],
                        title=r["title"],
                        scheduledTime=r["scheduledTime"],
                        recurring=r.get("recurring"),
                        completed=r.get("completed", False),
                        createdAt=r.get("createdAt", ""),
                    )
                    for r in data
                ]
            except Exception:
                return []

    def add_reminder(self, title: str, scheduled_time: str, recurring: str | None = None) -> ReminderItem:
        with self._lock:
            reminders = self.list_reminders()
            item = ReminderItem(
                id=f"rem_{uuid4().hex[:6]}",
                title=title.strip(),
                scheduledTime=scheduled_time.strip(),
                recurring=recurring,
                completed=False,
                createdAt=datetime.now().isoformat(),
            )
            reminders.append(item)
            self._save(reminders)
            return item

    def delete_reminder(self, reminder_id: str) -> bool:
        with self._lock:
            reminders = self.list_reminders()
            new_list = [r for r in reminders if r.id != reminder_id]
            if len(new_list) != len(reminders):
                self._save(new_list)
                return True
            return False

    def toggle_reminder(self, reminder_id: str) -> ReminderItem | None:
        with self._lock:
            reminders = self.list_reminders()
            target = None
            for r in reminders:
                if r.id == reminder_id:
                    r.completed = not r.completed
                    target = r
                    break
            if target:
                self._save(reminders)
            return target

    def _save(self, reminders: list[ReminderItem]) -> None:
        payload = [r.model_dump(by_alias=True) for r in reminders]
        self.storage_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


reminder_service = ReminderService()
