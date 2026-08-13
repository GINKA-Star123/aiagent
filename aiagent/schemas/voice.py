from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _metadata_value(value: Any) -> Any:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return enum_value

    return value


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    for key, value in metadata.items():
        normalized = _metadata_value(value)
        if normalized is None:
            continue
        cleaned[str(key)] = normalized

    return cleaned


class VoiceCallStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    ERROR = "error"


class VoiceTurnPhase(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EMPTY_TURN = "empty_turn"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceRealtimeCall(BaseModel):
    call_id: str
    user_id: str = "guest"
    username: str = "guest"

    status: VoiceCallStatus = VoiceCallStatus.ACTIVE
    phase: VoiceTurnPhase = VoiceTurnPhase.IDLE

    started_at: str = Field(default_factory=_now_iso)
    last_seen_at: str = Field(default_factory=_now_iso)
    phase_changed_at: str = Field(default_factory=_now_iso)
    ended_at: str = ""

    turn_count: int = 0
    last_turn_id: str = ""

    last_transcript: str = ""
    last_output_id: str = ""

    last_audio_path: str = ""
    last_audio_url: str = ""

    interrupt_count: int = 0
    last_interrupt_reason: str = ""

    last_error: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.last_seen_at = _now_iso()

    def update_metadata(self, **metadata: Any) -> None:
        cleaned = _clean_metadata(metadata)
        if cleaned:
            self.metadata.update(cleaned)

    def mark_phase(self, phase: VoiceTurnPhase, **metadata: Any) -> None:
        self.phase = phase
        self.phase_changed_at = _now_iso()
        self.touch()

        merged = _clean_metadata(metadata)
        merged["voice_realtime_status"] = self.status
        merged["voice_realtime_phase"] = self.phase
        self.update_metadata(**merged)