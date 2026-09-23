from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile

from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.task_queue import CloudTaskQueue
from cloud.timeouts import to_thread_with_timeout
from apps.api.response_utils import error_message_response, error_response, ok_response
from apps.api.request_context import get_request_id
from apps.core.runtime_registry import get_runtime, get_runtime_error
from config.settings import settings
from aiagent.graphs.graph_model import VISION_ANALYZE_SCHEMA_VERSION

router = APIRouter()
logger = logging.getLogger("aiagent.api.vision")
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)

# 与 ImageStore.allowed_extensions 对齐的 MIME 白名单。
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _validate_upload(file: UploadFile) -> str:
    """上传前置校验：返回错误信息，空串表示通过。

    目的是在调用视觉模型之前就挡掉明显不合法的上传，
    避免为了一个坏文件白跑一次 CLIP + 视觉模型。
    """
    content_type = (file.content_type or "").strip().lower()
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return f"Unsupported image content type: {content_type}"

    size = getattr(file, "size", None)
    if isinstance(size, int) and size > settings.vision_max_image_bytes:
        return (
            f"Image is too large. Max bytes: {settings.vision_max_image_bytes}, got {size}"
        )

    if isinstance(size, int) and size == 0:
        return "Image is empty."

    return ""


@router.post("/vision/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    user_id: str = Form(default="guest"),
    prompt: str = Form(default=""),
):
    upload_error = _validate_upload(file)
    if upload_error:
        return error_message_response(stage="vision_upload", error=upload_error, status_code=400)

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
        if cloud_settings.cloud_mode:
            result = await to_thread_with_timeout(
                "vision_analyze",
                settings.vision_timeout_seconds,
                runtime.analyze_image_upload,
                file_obj=file.file,
                filename=file.filename or "upload.png",
                user_prompt=prompt,
                user_id=user_id,
            )
        else:
            result = await asyncio.to_thread(
                runtime.analyze_image_upload,
                file_obj=file.file,
                filename=file.filename or "upload.png",
                user_prompt=prompt,
                user_id=user_id,
            )

        return ok_response(result=result.model_dump(mode="json"))

    except ValueError as exc:
        # ImageStore 抛出的都是"用户上传问题"，返回 400 而不是 500。
        logger.warning("Vision upload rejected: %s", exc)
        return error_message_response(stage="vision_upload", error=str(exc), status_code=400)

    except Exception as exc:
        logger.exception("Vision analyze failed: %s", exc)
        return error_response(stage="vision_analyze", exc=exc, status_code=500)


@router.post("/vision/chat")
async def vision_chat(
    file: UploadFile = File(...),
    user_id: str = Form(default="guest"),
    username: str = Form(default="guest"),
    prompt: str = Form(default="请看这张图片。"),
):
    upload_error = _validate_upload(file)
    if upload_error:
        return error_message_response(stage="vision_upload",error=upload_error,status_code=400)
    
    try:
        runtime = get_runtime()
    except ValueError as exc:
        logger.warning("Vision chat upload rejected %s",exc)
        return error_message_response(stage="vision_upload",error=str(exc),status_code=400)
    except Exception as exc:
        logger.exception("Runtime init failed in /vision/chat: %s", exc)
        return error_response(
            stage="runtime_init",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
        )

    try:
        if cloud_settings.cloud_mode:
            output = await to_thread_with_timeout(
                "vision_chat",
                settings.vision_timeout_seconds + settings.llm_timeout_seconds + 10.0,
                runtime.handle_vision_chat_upload,
                file_obj=file.file,
                filename=file.filename or "upload.png",
                user_prompt=prompt,
                user_id=user_id,
                username=username,
            )
        else:
            output = await asyncio.to_thread(
                runtime.handle_vision_chat_upload,
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
async def rebuild_character_index(
    force_rebuild: bool = True,
    _: None = Depends(require_cloud_admin),
):
    try:
        if cloud_settings.cloud_mode:
            task = await task_queue.enqueue(
                "vision.characters.rebuild",
                payload={"force_rebuild": force_rebuild},
                unique_key="vision.characters.rebuild",
                unique_ttl_seconds=3600,
                request_id=get_request_id(),
            )
            return ok_response(
                mode="task",
                task_id=task.task_id,
                created=task.created,
                status=task.status,
            )

        runtime = get_runtime()
        stats = runtime.rebuild_vision_character_index(force_rebuild=force_rebuild)
        return ok_response(mode="sync", stats=stats)

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

@router.get("/vision/schema")
def vision_schema():
    """返回当前视觉契约版本与支持的类型/通道，便于客户端与排查对齐。"""
    return ok_response(
        schema_version=VISION_ANALYZE_SCHEMA_VERSION,
        image_types=[
            "character", "daily", "screenshot", "document",
            "food", "travel", "landscape", "object", "unknown",
        ],
        channels=["ocr", "scene", "character"],
        channel_statuses=["ok", "partial", "missing", "skipped"],
        memory_reason_codes=[
            "confirmed_character_identity",
            "scene_preference_signal",
            "sensitive_content",
            "unknown_image_type",
            "unconfirmed_character_identity",
            "transient_document_image",
            "possible_real_person_identity",
            "model_not_considering",
            "low_confidence_scene",
            "unsupported_image_type",
        ],
        allowed_content_types=sorted(ALLOWED_IMAGE_CONTENT_TYPES),
        max_image_bytes=settings.vision_max_image_bytes,
    )