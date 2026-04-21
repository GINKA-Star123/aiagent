"""Speech playback and interruption state."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel,Field

class SpeakingState(BaseModel):
    is_speaking : bool = False
    current_text : str = ""
    last_audio_path : str = ""
    current_audio_path : str = ""

    playback_status :str = "idle"
    is_interrupted : bool = False
    last_stop_reason : str = ""

    last_tts_text : str = ""
    current_provider:str = ""
    audio_duration_sec :float = 0.0

    playback_started_at :str = ""
    playback_finished_at : str = ""
    last_updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    