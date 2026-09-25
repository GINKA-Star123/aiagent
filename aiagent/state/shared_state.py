from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

SHARED_STATE_SCHEMA_VERSION = "1.0"
DEFAULT_THREAD_TTL_SECONDS = 1800
DEFAULT_SESSION_TTL_SECONDS = 86400
DEFAULT_MAX_THREADS_PER_USER = 100

class SharedStateName(StrEnum):
    THREAD_OWNER = "thread_owner"
    THREAD_METADATA = "thread_metadata"
    SESSION_METADATA = "session_metadata"
    USER_THREADS = "user_threads"
    PERSONA_ACTIVE = "persona_active"

class SharedStateError(RuntimeError):
    stage = "shared_state"

class SharedStateUnavailableError(SharedStateError):
    stage = "shared_state_unavailable"

class SharedStateConflictError(SharedStateError):
    stage = "shared_state_conflict"

class SharedStateOwnershipError(SharedStateError):
    stage = "shared_state_ownership"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(slots=True)
class SessionRecord:
    session_id: str
    user_id: str
    thread_id: str
    version: int = 0
    fence: int = 0
    deleted: bool = False
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SHARED_STATE_SCHEMA_VERSION,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "version": self.version,
            "fence": self.fence,
            "deleted": self.deleted,
            "updated_at": self.updated_at
        }

@dataclass(slots=True)
class ThreadOwnerRecord:
    thread_id: str
    user_id: str
    session_id: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str,Any]:
        return {
            "schema_version": SHARED_STATE_SCHEMA_VERSION,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
