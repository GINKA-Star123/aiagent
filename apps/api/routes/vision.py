from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, UploadFile

from apps.api.response_utils import error_response, ok_response
from apps.core.runtime_registry import get_runtime, get_runtime_error

router = APIRouter()
logger = logging.getLogger("aiagent.api.vision")


@router.post("/vision/analyze")
def analyze_image(
    file: UploadFile = File(...),
    user_id: str = Form(default="guest"),
    prompt: str = Form(default=""),
):
    try:
        runtime = get_runtime()
    except Exception as exc:
        logger.exception("Runtime init failed in /vision/analyze: %s", exc)
        return error_response(
            stage="runtime_init",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
        )

    try:
        result = runtime.analyze_image_upload(
            file_obj=file.file,
            filename=file.filename or "upload.png",
            user_prompt=prompt,
            user_id=user_id,
        )

        return ok_response(
            result=result.model_dump(mode="json"),
        )
    except Exception as exc:
        logger.exception("Vision analyze failed: %s", exc)
        return error_response(stage="vision_analyze", exc=exc, status_code=500)


@router.post("/vision/chat")
def vision_chat(
    file: UploadFile = File(...),
    user_id: str = Form(default="guest"),
    username: str = Form(default="guest"),
    prompt: str = Form(default="请看这张图片。"),
):
    try:
        runtime = get_runtime()
    except Exception as exc:
        logger.exception("Runtime init failed in /vision/chat: %s", exc)
        return error_response(
            stage="runtime_init",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
        )

    try:
        output = runtime.handle_vision_chat_upload(
            file_obj=file.file,
            filename=file.filename or "upload.png",
            user_prompt=prompt,
            user_id=user_id,
            username=username,
        )

        packet = output["chat_output"].packet
        vision_state = output["vision_state"]
        vision_result = vision_state["vision_result"]

        return ok_response(
            output_id=output["chat_output"].output_id,
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
            vision={
                "result": vision_result.model_dump(mode="json"),
                "chat_context": vision_state.get("chat_context", ""),
                "memory_hint": vision_state.get("memory_hint", ""),
                "live2d_suggestion": vision_state.get("live2d_suggestion", {}),
                "metadata": vision_state.get("metadata", {}),
            },
        )
    except Exception as exc:
        logger.exception("Vision chat failed: %s", exc)
        return error_response(stage="vision_chat", exc=exc, status_code=500)


@router.post("/vision/characters/rebuild")
def rebuild_character_index(force_rebuild: bool = True):
    try:
        runtime = get_runtime()
        stats = runtime.rebuild_vision_character_index(force_rebuild=force_rebuild)
        return ok_response(stats=stats)
    except Exception as exc:
        logger.exception("Vision character rebuild failed: %s", exc)
        return error_response(stage="vision_character_rebuild", exc=exc, status_code=500)


@router.get("/vision/characters/stats")
def character_index_stats():
    try:
        runtime = get_runtime()
        stats = runtime.get_vision_character_index_stats()
        return ok_response(stats=stats)
    except Exception as exc:
        logger.exception("Vision character stats failed: %s", exc)
        return error_response(stage="vision_character_stats", exc=exc, status_code=500)
