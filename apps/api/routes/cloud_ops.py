from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from apps.api.response_utils import json_response, ok_response
from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.readiness import build_ops_readiness
from cloud.task_queue import CloudTaskQueue

router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


def _path_status(path: str) -> dict[str, object]:
    target = Path(path)
    return {
        "path": path,
        "exists": target.exists(),
        "is_dir": target.is_dir(),
    }


@router.get("/cloud/ops/readiness")
async def readiness(_: None = Depends(require_cloud_admin)):
    snapshot = await build_ops_readiness(task_queue=task_queue)
    return json_response(snapshot.model_dump(mode="json"))


@router.get("/cloud/ops/config-snapshot")
async def config_snapshot(_: None = Depends(require_cloud_admin)):
    return ok_response(
        cloud={
            "cloud_mode": cloud_settings.cloud_mode,
            "region": cloud_settings.cloud_deploy_region,
            "rate_limit_enabled": cloud_settings.rate_limit_enabled,
            "inflight_limit_enabled": cloud_settings.inflight_limit_enabled,
            "storage_provider": cloud_settings.storage_provider,
            "global_inflight_limit": cloud_settings.global_inflight_limit,
            "chat_inflight_limit": cloud_settings.chat_inflight_limit,
            "voice_inflight_limit": cloud_settings.voice_inflight_limit,
            "multimodal_inflight_limit": cloud_settings.multimodal_inflight_limit,
        },
        paths={
            "data": _path_status("data"),
            "cache": _path_status("data/cache"),
            "knowledge": _path_status("data/knowledge"),
            "characters": _path_status("data/characters"),
        },
        gpu={
            "llm": bool(cloud_settings.gpu_llm_base_url),
            "tts": bool(cloud_settings.gpu_tts_base_url),
            "asr": bool(cloud_settings.gpu_asr_base_url),
        },
        admin={
            "token_configured": True,
            "header": "x-cloud-admin-token",
        },
    )