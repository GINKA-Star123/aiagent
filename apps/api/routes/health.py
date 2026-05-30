from __future__ import annotations

from fastapi import APIRouter

from cloud.config import cloud_settings
from cloud.gpu_client import gpu_client
from cloud.redis_client import redis_health
from apps.core.runtime_registry import get_runtime_error
from apps.api.response_utils import ok_response

router = APIRouter()


@router.get("/live")
def live_check():
    return ok_response(status = "alive")

@router.get("/health")
def health_check():
    return ok_response(
        status="ok",
        cloud_mode = cloud_settings.cloud_mode,
    )

@router.get("/ready")
async def ready_check():
    redis = await redis_health()
    gpu = await gpu_client.health_all()

    checks = {
        "runtime_import": get_runtime_error() is None,
        "redis": redis.get("ok", False) if cloud_settings.redis_url else not cloud_settings.cloud_mode,
        "storage_provider": cloud_settings.storage_provider in {"local", "cos", "s3"},
        "gpu_llm": _gpu_ready(gpu["llm"], required=cloud_settings.cloud_mode),
        "gpu_tts": _gpu_ready(gpu["tts"], required=False),
        "gpu_asr": _gpu_ready(gpu["asr"], required=False),
    }

    ready = all(checks.values())

    return {
        "ok":ready,
        "status":"ready" if ready else "not_ready",
        "checks":checks,
        "redis":redis,
        "gpu":gpu,
    }

def _gpu_ready(item:dict,*,required:bool)->bool:
    if not required and not item.get("configured", False):
        return True
    return bool(item.get("ok", False))