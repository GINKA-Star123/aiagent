"""Output payload schema definitions."""
from datetime import datetime
from uuid import uuid4
from enum import StrEnum

from pydantic import BaseModel,Field


class EmotionLabel(StrEnum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    ANGRY = "angry"

class ResponsePacket(BaseModel):
    reply_text : str
    base_reply_text : str | None = None
    emotion : EmotionLabel = EmotionLabel.NEUTRAL
    should_speak : bool = True
    should_store_memory : bool = False
    motion : str | None = None
    audio_path : str | None = None
    metadata: dict[str,str] = Field(default_factory=dict)


class OutputEvent(BaseModel):
    output_id : str = Field(default_factory=lambda: str(uuid4()))
    timestamp : datetime = Field(default_factory=datetime.now)
    packet : ResponsePacket