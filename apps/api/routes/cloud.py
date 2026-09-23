from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from apps.api.response_utils import (
    error_message_response,
    error_response,
    ok_response,
)
from cloud.config import cloud_settings
from cloud.object_storage import (
    ObjectStorageError,
    build_object_key,
    get_object_store,
    guess_content_type,
    normalize_content_type,
    normalize_expires_seconds,
    normalize_filename,
    normalize_storage_prefix,
    stored_object_payload,
)
from cloud.redis_client import redis_health


router = APIRouter()


class PresignUploadRequest(BaseModel):
    """
    预签名上传请求模型。
    """

    filename: str = Field(
        ...,
        min_length=1,
        max_length=240,
        description="原始文件名",
    )
    content_type: str = Field(
        default="application/octet-stream",
        max_length=128,
        description="文件 MIME 类型",
    )
    prefix: str = Field(
        default="uploads",
        max_length=120,
        description="对象存储目录前缀",
    )
    expires_seconds: int = Field(
        default=900,
        ge=60,
        le=3600,
        description="预签名 URL 有效期，单位为秒",
    )


@router.get("/cloud/ready")
async def cloud_ready():
    """
    返回 Cloud 基础设施状态。

    该接口用于普通服务状态查看，
    不等价于云生产流量接入前的完整运维 readiness。
    """

    return ok_response(
        cloud_mode=cloud_settings.cloud_mode,
        region=cloud_settings.cloud_deploy_region,
        redis=await redis_health(),
        storage={
            "provider": cloud_settings.storage_provider.strip().lower(),
            "bucket_configured": bool(cloud_settings.s3_bucket),
            "public_base_url_configured": bool(
                cloud_settings.s3_public_base_url
            ),
        },
        gpu={
            "llm_configured": bool(cloud_settings.gpu_llm_base_url),
            "tts_configured": bool(cloud_settings.gpu_tts_base_url),
            "asr_configured": bool(cloud_settings.gpu_asr_base_url),
        },
    )


@router.get("/cloud/limits")
def cloud_limits():
    """
    返回当前 Cloud 限流及并发限制配置。
    """

    return ok_response(
        rate_limit_enabled=cloud_settings.rate_limit_enabled,
        inflight_limit_enabled=cloud_settings.inflight_limit_enabled,
        limits={
            "global_inflight": cloud_settings.global_inflight_limit,
            "chat_inflight": cloud_settings.chat_inflight_limit,
            "multimodal_inflight": cloud_settings.multimodal_inflight_limit,
            "voice_inflight": cloud_settings.voice_inflight_limit,
            "rebuild_inflight": cloud_settings.rebuild_inflight_limit,
            "chat_per_minute": cloud_settings.rate_limit_chat_per_minute,
            "multimodal_per_minute": (
                cloud_settings.rate_limit_multimodal_per_minute
            ),
            "voice_per_minute": cloud_settings.rate_limit_voice_per_minute,
            "rebuild_per_minute": cloud_settings.rate_limit_rebuild_per_minute,
        },
    )


@router.post("/cloud/storage/presign-upload")
async def presign_upload(req: PresignUploadRequest):
    """
    创建对象存储预签名上传 URL。

    Local 存储会明确返回不支持，
    S3/COS 存储则返回可直接交给客户端使用的 URL。
    """

    try:
        filename = normalize_filename(req.filename)
        content_type = normalize_content_type(req.content_type)
        prefix = normalize_storage_prefix(req.prefix)
        expires_seconds = normalize_expires_seconds(req.expires_seconds)

        key = build_object_key(prefix, filename)
        store = get_object_store()

        upload_url = await store.presigned_put_url(
            key=key,
            content_type=content_type,
            expires_seconds=expires_seconds,
        )

    except ObjectStorageError as exc:
        return error_message_response(
            stage=exc.stage,
            error=str(exc),
            status_code=400,
        )
    except Exception as exc:
        return error_response(
            stage="presign_upload",
            exc=exc,
            status_code=503,
            include_traceback=False,
        )

    return ok_response(
        key=key,
        upload_url=upload_url,
        content_type=content_type,
        expires_seconds=expires_seconds,
        storage_provider=cloud_settings.storage_provider.strip().lower(),
    )


@router.post("/cloud/storage/upload")
async def direct_upload(
    prefix: str = Form(default="uploads"),
    file: UploadFile = File(...),
):
    """
    接收 Multipart 文件并写入对象存储。
    """

    if not file.filename or not file.filename.strip():
        return error_message_response(
            stage="upload_validation",
            error="filename is required",
            status_code=400,
        )

    try:
        filename = normalize_filename(file.filename)
        safe_prefix = normalize_storage_prefix(prefix)

        data = await file.read()

        if len(data) > cloud_settings.upload_max_bytes:
            return error_message_response(
                stage="upload_size_limit",
                error="uploaded file is too large",
                status_code=413,
                extra={
                    "max_bytes": cloud_settings.upload_max_bytes,
                    "actual_bytes": len(data),
                },
            )

        content_type = normalize_content_type(
            file.content_type
            or guess_content_type(filename)
        )

        key = build_object_key(
            prefix=safe_prefix,
            filename=filename,
        )

        stored = await get_object_store().put_bytes(
            key=key,
            data=data,
            content_type=content_type,
        )

    except ObjectStorageError as exc:
        return error_message_response(
            stage=exc.stage,
            error=str(exc),
            status_code=400,
        )
    except Exception as exc:
        return error_response(
            stage="direct_upload",
            exc=exc,
            status_code=503,
            include_traceback=False,
        )

    return ok_response(
        object=stored_object_payload(stored),
    )