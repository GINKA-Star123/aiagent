"""Input payload schema definitions."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum , StrEnum
from uuid import uuid4
from typing import Any

from pydantic import BaseModel,Field


class InputSource(StrEnum):
    CHAT = "chat"
    ASR = "asr"
    VISION = "vision"
    MULTIMODAL = "multimodal"
    SYSTEM = "system"

class EventPriority(IntEnum):
    LOW = 1
    NORMAL = 5
    HIGH = 10

class InputAttachment(BaseModel):
    type:str
    path:str
    filename:str = ""
    mime_type : str = ""
    image_id : str =""
    metadata:dict[str,Any] = Field(default_factory=dict)

class InputEvent(BaseModel):
    event_id : str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)

    source: InputSource
    user_id : str ="guest"
    user_name : str ="guest"
    text : str = ""

    modality : str = "text"
    attachments:list[InputAttachment] = Field(default_factory=list)
    priority : EventPriority = EventPriority.NORMAL
    metadata: dict[str,str] = Field(default_factory=dict)