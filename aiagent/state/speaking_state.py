"""Speech playback and interruption state."""

from pydantic import BaseModel

class SpeakingState(BaseModel):
    is_speaking : bool = False
    current_text : str = ""
    last_audio_path : str = ""