from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, UploadFile
from starlette.responses import JSONResponse

from cloud.config import cloud_settings
from cloud.degrade import degraded_chat_response
from cloud.timeouts import CloudTimeoutError,to_thread_with_timeout
from apps.api.response_utils import error_response, ok_response
from apps.core.runtime_registry import get_runtime, get_runtime_error
from config.settings import settings

router = APIRouter()
logger = logging.getLogger("aiagent.api.multimodal_chat")


@router.post("/chat/multimodal")
async def multimodal_chat(
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
        if cloud_settings.cloud_mode:
            output = await to_thread_with_timeout(
                "multimodal_chat",
                max(15.0,settings.vision_timeout_seconds+settings.llm_timeout_seconds+settings.tts_timeout_seconds),
                runtime.handle_multimodal_chat_upload,
                file_obj = file.file if file is not None else None,
                filename = file.filename if file is not None else "",
                text=text,
                user_id = user_id,
                username = username
            )

        else:
            import asyncio

            output = await asyncio.to_thread(
                runtime.handle_multimodal_chat_upload,
                file_obj = file.file if file is not None else None,
                filename = file.filename if file is not None else "", # type: ignore
                text=text,
                user_id = user_id,
                username = username
            )
        
        packet = output.packet

        return ok_response(
            output_id = output.output_id,
            replt = packet.reply_text,
            base_reply_text = packet.base_reply_text,
            emotion = packet.emotion,
            motion = packet.motion,
            expression = packet.expression,
            audio_path = packet.audio_path,
            audio_url = packet.audio_url,
            audio_segments = packet.audio_segments,
            audio_segment_urls = packet.audio_segment_urls,
            audio_segments_texts = packet.audio_segment_texts,
            live2d_command_path = packet.live2d_command_path,
            metadata = packet.metadata,
        )
    
    except CloudTimeoutError as exc:
        logger.warning("Multimodal chat timed out: %s", exc)
        return JSONResponse(
            status_code=504,
            content = degraded_chat_response(
                stage=exc.stage,
                error = str(exc),
                user_text = text,
                retry_after_seconds = 5
            )
        )
    except Exception as exc:
        logger.exception("Multimodal chat failed: %s", exc)
        if cloud_settings.cloud_mode:
            return JSONResponse(
                status_code=503,
                content=degraded_chat_response(
                    stage="multimodal_chat_handler",
                    error=str(exc),
                    user_text=text,
                    retry_after_seconds=5,
                ),
            )
        return error_response(stage="chat", exc=exc, status_code=500)