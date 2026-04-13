"""Event bus for normalized system events."""
from collections import defaultdict
from collections.abc import Callable

from aiagent.schemas.events import SystemEvent, SystemEventType


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[SystemEventType, list[Callable[[SystemEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: SystemEventType, handler: Callable[[SystemEvent], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: SystemEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
