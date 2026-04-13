"""Chat route placeholder."""

from fastapi import APIRouter
from pydantic import BaseModel

from apps.core.bootstrap import build_runtime

router = APIRouter()
runtime = build_runtime()

class ChatRequest(BaseModel):
    user_id: str
    username: str
    text: str

@router.post("/chat")
def chat(request: ChatRequest):
    """Chat endpoint."""
    reply = runtime.handle_chat(
        text=request.text,
        user_id=request.user_id,
        username=request.username,
    )
    return {"reply": reply}