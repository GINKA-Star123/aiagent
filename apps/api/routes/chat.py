"""Chat route placeholder."""

import json

from fastapi import APIRouter, Response
from pydantic import BaseModel

from apps.core.bootstrap import build_runtime

router = APIRouter()
runtime = build_runtime()


class ChatRequest(BaseModel):
    user_id: str
    username: str
    text: str


@router.post("/chat")
def chat(req: ChatRequest):
    output = runtime.handle_chat_full(
        text=req.text,
        user_id=req.user_id,
        username=req.username,
    )

    body = json.dumps(
        {
            "reply": output.packet.reply_text,
            "base_reply_text": output.packet.base_reply_text,
            "emotion": output.packet.emotion,
            "motion": output.packet.motion,
            "audio_path": output.packet.audio_path,
            "metadata": output.packet.metadata,
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )
