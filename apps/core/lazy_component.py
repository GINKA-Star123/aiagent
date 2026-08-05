from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Generic, TypeVar

from apps.core.capabilities import CapabilityRegistry

T = TypeVar("T")

class LazyComponent(Generic[T]):
    def __init__(
            self,
            *,
            name:str,
            factory:Callable[[],T],
            capabilities:CapabilityRegistry,
            summary:str = "",
    ) ->None:
        self.name = name
        self.factory = factory
        self.capabilities = capabilities
        self.summary = summary or f"{name} lazy component"
        self._value:T|None = None
        self._lock = RLock()

        self.capabilities.mark_disabled(
            name,
            f"{self.summary} is not initialized yet.",
            details = {
                "lazy":True,
            },
        )

    def get(self) -> T:
        if self._value is not None:
            return self._value

        with self._lock:
            if self._value is not None:
                return self._value

            self.capabilities.mark_initializing(
                self.name,
                f"{self.summary} is initializing.",
                details = {
                    "lazy":True,
                },
            )
            try:
                value = self.factory()
            except Exception as exc:
                self.capabilities.mark_error(
                    self.name,
                    f"""{self.summary} failed to initialize: {exc}""",
                    details = {
                        "lazy":True,
                    },
                    error = exc,
                )
                raise

            self._value = value
            self.capabilities.mark_available(
                self.name,
                f"{self.summary} is available.",
                details = {
                    "lazy":True,
                    "initialized":True,
                },
            )
            return value

    def is_initialized(self) -> bool:
        return self._value is not None

    def reset(self) ->None:
        with self._lock:
            self._value = None
            self.capabilities.mark_disabled(
                self.name,
                f"{self.summary} has been reset.",
                details = {
                    "lazy":True,
                    "initialized":False,
                },
            )