"""Current emotion state."""
from pydantic import BaseModel

from aiagent.schemas.outputs import EmotionLabel


class EmotionState(BaseModel):
    current_emotion: EmotionLabel = EmotionLabel.NEUTRAL
