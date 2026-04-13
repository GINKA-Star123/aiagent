"""Global agent runtime state."""

from enum import StrEnum

from pydantic import BaseModel

class AgentStatus(StrEnum):
    """Agent status."""
    IDLE = "idle"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"

class AgentRuntimeState(BaseModel):
    """Agent runtime state."""
    status: AgentStatus = AgentStatus.IDLE
    current_session_id: str = "default"
    last_input_id : str|None = None
    last_output_id : str|None = None
    error_message : str|None = None
    