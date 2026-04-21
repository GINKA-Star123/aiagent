"""Current stream and room state."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel,Field

class StreamingState(BaseModel):
    is_listening: bool = False
    is_processing_voice :bool = False

    last_recording_path : str = ""
    last_transcript : str = ""
    last_error : str = ""

    last_session_status:str ="idle"
    last_interrupt_reason:str =  ""
    last_updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))