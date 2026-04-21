import json
import logging
import traceback

from fastapi import APIRouter, Response
from pydantic import BaseModel

from apps.core.runtime_registry import get_runtime, get_runtime_error

router = APIRouter()
logger = logging.getLogger("aiagent.api.chat")


class ChatRequest(BaseModel):
    user_id: str
    username: str
    text: str


@router.post("/chat")
def chat(req: ChatRequest):
    try:
        runtime = get_runtime()
    except Exception as exc:
        logger.exception("Runtime init failed in /chat: %s", exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "runtime_init",
                "error": str(exc),
                "runtime_error": get_runtime_error(),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )

    try:
        output = runtime.handle_chat_full(
            text=req.text,
            user_id=req.user_id,
            username=req.username,
        )

        body = json.dumps(
            {
                "ok": True,
                "reply": output.packet.reply_text,
                "base_reply_text": output.packet.base_reply_text,
                "emotion": output.packet.emotion,
                "motion": output.packet.motion,
                "expression": output.packet.expression,
                "audio_path": output.packet.audio_path,
                "live2d_command_path": output.packet.live2d_command_path,
                "metadata": output.packet.metadata,
            },
            ensure_ascii=False,
        )

        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=200,
        )

    except Exception as exc:
        logger.exception("Chat route failed: %s", exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "chat_handler",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )
