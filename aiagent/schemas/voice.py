from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

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
    username:str = "guest"

    status: VoiceCallStatus = VoiceCallStatus.ACTIVE
    phase: VoiceTurnPhase = VoiceTurnPhase.IDLE

    started_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_seen_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
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
    metadata: dict[str,Any] = Field(default_factory=dict)

    def touch(self) ->None:
        self.last_seen_at = datetime.now().isoformat(timespec="seconds")

    def mark_phase(self,phase:VoiceTurnPhase,**metadata:Any) ->None:
        self.phase = phase
        self.touch()
        if metadata:
            self.metadata.update(metadata)