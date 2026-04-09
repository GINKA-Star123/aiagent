"""Event bus for normalized system events."""
from collections import defaultdict
from collections.abc import Callable

from aiagent.schemas.events import SystemEvents, SystemEventType


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[SystemEventType, list[Callable[[SystemEvents], None]]] = defaultdict(list)

    def subscribe(self, event_type: SystemEventType, handler: Callable[[SystemEvents], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: SystemEvents) -> None:
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
