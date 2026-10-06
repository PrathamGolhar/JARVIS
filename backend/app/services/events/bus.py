"""
JARVIS 2.0 — Asynchronous Event Bus.
Provides decoupled publish/subscribe event messaging across agents, tools, speech, file monitors, and UI notifications.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("jarvis.event_bus")


class EventType(str, Enum):
    FILE_UPLOADED = "FILE_UPLOADED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    VOICE_STARTED = "VOICE_STARTED"
    VOICE_STOPPED = "VOICE_STOPPED"
    MEMORY_UPDATED = "MEMORY_UPDATED"
    AUTOMATION_TRIGGERED = "AUTOMATION_TRIGGERED"
    ACTION_CONFIRMED = "ACTION_CONFIRMED"
    DIAGNOSTICS_PROBED = "DIAGNOSTICS_PROBED"


@dataclass
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str | None = None


EventHandler = Callable[[Event], Coroutine[Any, Any, None] | None]


class EventBus:
    """Singleton event bus supporting sync and async event listeners."""

    _instance: "EventBus | None" = None

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = {et: [] for et in EventType}
        self._event_history: list[Event] = []

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: EventType, payload: dict[str, Any] | None = None) -> Event:
        event = Event(type=event_type, payload=payload or {})
        self._event_history.append(event)
        # Keep last 200 events in memory
        if len(self._event_history) > 200:
            self._event_history = self._event_history[-200:]

        logger.debug("EventBus: Publishing event '%s' -> %s", event_type.value, payload)

        listeners = self._subscribers.get(event_type, [])
        for handler in listeners:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error("EventBus: Error in event listener for '%s': %s", event_type.value, exc)

        return event

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "type": e.type.value,
                "payload": e.payload,
                "timestamp": e.timestamp,
            }
            for e in reversed(self._event_history[-limit:])
        ]


# Global convenient accessor
event_bus = EventBus.get_instance()
