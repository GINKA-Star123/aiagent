from __future__ import annotations

from datetime import datetime,timezone
from enum import StrEnum
from threading import RLock
from typing import Any

from pydantic import BaseModel,Field

class CapabilityStatus(StrEnum):
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    AVAILABLE = "available"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    ERROR = "error"

class CapabilityRecord(BaseModel):
    name:str
    status:CapabilityStatus = CapabilityStatus.UNKNOWN
    summary:str = ""
    details:dict[str,Any] = Field(default_factory=dict)
    error:str = ""
    updated_at :str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

class CapabilityRegistry:
    def __init__(self)->None:
        self._items :dict[str,CapabilityRecord] = {}
        self._lock = RLock()

    def set(
            self,
            name:str,
            status:CapabilityStatus,
            summary:str = "",
            *,
            details:dict[str,Any]|None = None,
            error:str|None = None,
    ) ->None:
        with self._lock:
            self._items[name] = CapabilityRecord(
                name=name,
                status=status,
                summary=summary,
                details=details or {},
                error=error or "",
            )

    def mark_initializing(
        self,
        name: str,
        summary: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.set(
            name=name,
            status=CapabilityStatus.INITIALIZING,
            summary=summary,
            details=details,
        )

    def mark_available(
        self,
        name: str,
        summary: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.set(
            name=name,
            status=CapabilityStatus.AVAILABLE,
            summary=summary,
            details=details,
        )

    def mark_degraded(
        self,
        name: str,
        summary: str = "",
        *,
        details: dict[str, Any] | None = None,
        error: Exception | str | None = None,
    ) -> None:
        self.set(
            name=name,
            status=CapabilityStatus.DEGRADED,
            summary=summary,
            details=details,
            error=str(error) if error else None,
        )

    def mark_disabled(
        self,
        name: str,
        summary: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.set(
            name=name,
            status=CapabilityStatus.DISABLED,
            summary=summary,
            details=details,
        )

    def mark_error(
        self,
        name: str,
        summary: str = "",
        *,
        details: dict[str, Any] | None = None,
        error: Exception | str | None = None,
    ) -> None:
        self.set(
            name=name,
            status=CapabilityStatus.ERROR,
            summary=summary,
            details=details,
            error=str(error) if error else None,
        )

    def get(self, name: str) -> CapabilityRecord | None:
        with self._lock:
            return self._items.get(name)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            items = {
                name: record.model_dump(mode="json")
                for name, record in sorted(self._items.items())
            }

        summary = {
            "unknown": 0,
            "initializing": 0,
            "available": 0,
            "degraded": 0,
            "disabled": 0,
            "error": 0,
        }

        for item in items.values():
            status = str(item.get("status", "unknown"))
            summary[status] = summary.get(status, 0) + 1

        return {
            "ok": summary["error"] == 0,
            "status": self._overall_status(summary),
            "summary": summary,
            "items": items,
        }

    def _overall_status(self, summary: dict[str, int]) -> str:
        if summary.get("error", 0) > 0:
            return "error"
        if summary.get("degraded", 0) > 0:
            return "degraded"
        if summary.get("initializing", 0) > 0:
            return "initializing"
        if summary.get("available", 0) > 0:
            return "available"
        return "unknown"