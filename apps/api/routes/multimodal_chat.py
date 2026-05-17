from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, UploadFile

from apps.api.response_utils import error_response, ok_response
from apps.core.runtime_registry import get_runtime, get_runtime_error

router = APIRouter()
logger = logging.getLogger("aiagent.api.multimodal_chat")


@router.post("/chat/multimodal")
def multimodal_chat(
    file: UploadFile | None = File(default=None),
    user_id: str = Form(default="guest"),
    username: str = Form(default="guest"),
    text: str = Form(default=""),
):
    try:
        runtime = get_runtime()
    except Exception as exc:
        logger.exception("Runtime init failed in /chat/multimodal: %s", exc)
        return error_response(
            stage="runtime_init",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
        )

    try:
        output = runtime.handle_multimodal_chat_upload(
            file_obj=file.file if file is not None else None,
            filename=file.filename if file is not None else "", # type: ignore
            text=text,
            user_id=user_id,
            username=username,
        )

        packet = output.packet

        return ok_response(
            output_id=output.output_id,
            reply=packet.reply_text,
            base_reply_text=packet.base_reply_text,
            emotion=packet.emotion,
            motion=packet.motion,
            expression=packet.expression,
            audio_path=packet.audio_path,
            audio_url=packet.audio_url,
            audio_segments=packet.audio_segments,
            audio_segment_urls=packet.audio_segment_urls,
            audio_segment_texts=packet.audio_segment_texts,
            live2d_command_path=packet.live2d_command_path,
            live2d=packet.live2d,
            metadata=packet.metadata,
        )
    except Exception as exc:
        logger.exception("Multimodal chat failed: %s", exc)
        return error_response(stage="chat", exc=exc, status_code=500)
