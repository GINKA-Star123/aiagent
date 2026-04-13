"""Memory schema definitions."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel,Field

class MemoryKind(StrEnum):
    SHORT_TERM = "short_term"
    USER_PORFILE = "user_profile"

class MemoryItem(BaseModel):
    memory_id : str = Field(default_factory=lambda: str(uuid4()))
    user_id : str
    username : str
    content : str
    kind: MemoryKind
    timestamp : datetime = Field(default_factory=datetime.now)
    importance : float = 0.5