from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cloud.config import cloud_settings
from cloud.gpu_client import gpu_client
from cloud.redis_client import redis_health
from cloud.task_queue import CloudTaskQueue
from apps.core.runtime_registry import get_runtime_error


class ReadinessStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    NOT_READY = "not_ready"


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    required: bool = True
    summary: str = ""
    action: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ReadinessSnapshot(BaseModel):
    ok: bool
    status: ReadinessStatus
    checks: dict[str, bool]
    summary: dict[str, int]
    items: list[ReadinessCheck]
    cloud_mode: bool
    details: dict[str, Any] = Field(default_factory=dict)


async def build_public_readiness() -> ReadinessSnapshot:
    redis = await redis_health()
    gpu = await gpu_client.health_all()

    items = [
        _runtime_import_check(),
        _redis_check(redis),
        _storage_provider_check(),
        _gpu_check("gpu_llm", gpu.get("llm", {}), required=cloud_settings.cloud_mode),
        _gpu_check("gpu_tts", gpu.get("tts", {}), required=False),
        _gpu_check("gpu_asr", gpu.get("asr", {}), required=False),
    ]

    return _snapshot(
        items=items,
        details={
            "redis": redis,
            "gpu": gpu,
        },
    )


async def build_ops_readiness(task_queue: CloudTaskQueue | None = None) -> ReadinessSnapshot:
    redis = await redis_health()
    gpu = await gpu_client.health_all()

    items = [
        _runtime_import_check(),
        _redis_check(redis),
        _storage_provider_check(),
        _path_check("data_dir", "data", required=True),
        _path_check("cache_dir", "data/cache", required=False),
        _path_check("knowledge_dir", "data/knowledge", required=False),
        _path_check("characters_dir", "data/characters", required=False),
        _env_check("qdrant_configured", "QDRANT_HOST", required=False),
        _admin_token_check(required=True),
        _gpu_check("gpu_llm", gpu.get("llm", {}), required=cloud_settings.cloud_mode),
        _gpu_check("gpu_tts", gpu.get("tts", {}), required=False),
        _gpu_check("gpu_asr", gpu.get("asr", {}), required=False),
    ]

    queue_summary: dict[str, int] = {}
    if task_queue is not None:
        try:
            queue_summary = await task_queue.task_summary(queue="default")
            items.append(
                ReadinessCheck(
                    name="task_queue",
                    ok=True,
                    required=False,
                    summary="Task queue summary is available.",
                    details={"summary": queue_summary},
                )
            )
        except Exception as exc:
            items.append(
                ReadinessCheck(
                    name="task_queue",
                    ok=False,
                    required=False,
                    summary="Task queue summary failed.",
                    action="检查 Redis 或内存任务队列状态。",
                    details={"error": str(exc)},
                )
            )

    return _snapshot(
        items=items,
        details={
            "redis": redis,
            "gpu": gpu,
            "task_queue": queue_summary,
        },
    )


def _snapshot(*, items: list[ReadinessCheck], details: dict[str, Any]) -> ReadinessSnapshot:
    required_failed = [item for item in items if item.required and not item.ok]
    optional_failed = [item for item in items if not item.required and not item.ok]

    if required_failed:
        status = ReadinessStatus.NOT_READY
    elif optional_failed:
        status = ReadinessStatus.DEGRADED
    else:
        status = ReadinessStatus.READY

    return ReadinessSnapshot(
        ok=status != ReadinessStatus.NOT_READY,
        status=status,
        checks={item.name: item.ok for item in items},
        summary={
            "total": len(items),
            "required_failed": len(required_failed),
            "optional_failed": len(optional_failed),
        },
        items=items,
        cloud_mode=cloud_settings.cloud_mode,
        details=details,
    )


def _runtime_import_check() -> ReadinessCheck:
    error = get_runtime_error()
    return ReadinessCheck(
        name="runtime_import",
        ok=error is None,
        required=True,
        summary="Runtime import is healthy." if error is None else "Runtime import failed.",
        action="" if error is None else "查看启动日志并修复 runtime 初始化异常。",
        details={"error": error or ""},
    )


def _redis_check(redis: dict[str, Any]) -> ReadinessCheck:
    required = bool(cloud_settings.cloud_mode or cloud_settings.redis_url)
    ok = bool(redis.get("ok", False)) if required else True

    return ReadinessCheck(
        name="redis",
        ok=ok,
        required=required,
        summary="Redis is available." if ok else "Redis is unavailable or not configured.",
        action="" if ok else "检查 REDIS_URL、网络连通性和 Redis 服务状态。",
        details=redis,
    )


def _storage_provider_check() -> ReadinessCheck:
    provider = cloud_settings.storage_provider.strip().lower()
    ok = provider in {"local", "cos", "s3"}

    return ReadinessCheck(
        name="storage_provider",
        ok=ok,
        required=True,
        summary="Storage provider is supported." if ok else "Storage provider is unsupported.",
        action="" if ok else "将 STORAGE_PROVIDER 配置为 local、cos 或 s3。",
        details={"provider": cloud_settings.storage_provider},
    )


def _gpu_check(name: str, item: dict[str, Any], *, required: bool) -> ReadinessCheck:
    configured = bool(item.get("configured", False))
    ok = bool(item.get("ok", False)) if required or configured else True

    return ReadinessCheck(
        name=name,
        ok=ok,
        required=required,
        summary=f"{name} is ready." if ok else f"{name} is unavailable.",
        action="" if ok else "检查 GPU 服务 base url、鉴权 token、网络和服务健康接口。",
        details=item,
    )


def _path_check(name: str, path: str, *, required: bool) -> ReadinessCheck:
    target = Path(path)
    ok = target.exists()

    return ReadinessCheck(
        name=name,
        ok=ok if required else True,
        required=required,
        summary=f"{path} exists." if ok else f"{path} does not exist.",
        action="" if ok else f"创建目录 {path} 或检查挂载路径。",
        details={
            "path": path,
            "exists": target.exists(),
            "is_dir": target.is_dir(),
        },
    )


def _env_check(name: str, env_name: str, *, required: bool) -> ReadinessCheck:
    value = os.getenv(env_name, "").strip()
    ok = bool(value) if required else True

    return ReadinessCheck(
        name=name,
        ok=ok,
        required=required,
        summary=f"{env_name} is configured." if value else f"{env_name} is not configured.",
        action="" if ok else f"配置环境变量 {env_name}。",
        details={
            "env": env_name,
            "configured": bool(value),
        },
    )


def _admin_token_check(*, required: bool) -> ReadinessCheck:
    configured = bool(os.getenv("CLOUD_ADMIN_TOKEN", "").strip())
    ok = configured if required else True

    return ReadinessCheck(
        name="cloud_admin_token",
        ok=ok,
        required=required,
        summary="Cloud admin token is configured." if configured else "Cloud admin token is missing.",
        action="" if ok else "配置 CLOUD_ADMIN_TOKEN，避免管理接口无法安全访问。",
        details={"configured": configured},
    )