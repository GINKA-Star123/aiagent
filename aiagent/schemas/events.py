"""Event schema definitions."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel,Field


class SystemEventType(StrEnum):
    INPUT_RECEIVED = "input_received"
    RESPONSE_READY = "response_ready"
    ERROR  = "error"

class SystemEvent(BaseModel):
    event_id : str = Field(default_factory=lambda: str(uuid4()))
    event_type : SystemEventType
    payload : dict
    timestamp : datetime = Field(default_factory=datetime.now)
    metadata : dict[str,str] = Field(default_factory=dict)