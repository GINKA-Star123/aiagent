from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PresenceState = Literal[
    "idle",
    "reading",
    "thinking",
    "resting",
    "working",
    "listening",
    "focused",
    "sleepy",
]

OpeningKind = Literal[
    "first_meet",
    "short_return",
    "same_day_return",
    "next_day_return",
    "long_absence",
    "late_night",
    "task_resume",
]


class MoodState(BaseModel):
    valence: float = 0.45
    energy: float = 0.55
    fatigue: float = 0.2
    curiosity: float = 0.65
    warmth: float = 0.6


class SessionSnapshot(BaseModel):
    user_id: str
    username: str = "guest"
    last_opened_at: datetime | None = None
    last_topic: str = ""
    last_emotion: str = "neutral"
    unfinished_hint: str = ""
    open_count: int = 0
    mood: MoodState = Field(default_factory=MoodState)


class SessionOpenRequest(BaseModel):
    user_id: str = "guest"
    username: str = "guest"
    client_time: datetime | None = None
    entry: str = "chat_page"
    recent_topic: str = ""


class PresencePayload(BaseModel):
    state: PresenceState
    mood: str
    energy: float
    fatigue: float
    curiosity: float


class OpeningPayload(BaseModel):
    kind: OpeningKind
    text: str
    should_speak: bool = True


class Live2DPresencePayload(BaseModel):
    expression: str
    motion: str
    suggested_delay_ms: int
    eye: dict
    mouth: dict
    scene: dict


class SessionOpenResponse(BaseModel):
    ok: bool = True
    opening: OpeningPayload
    presence: PresencePayload
    live2d: Live2DPresencePayload
    memory: dict