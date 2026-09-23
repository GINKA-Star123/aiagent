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
from cloud.failure_policy import (
    FailureMode,
    describe_failure_policy,
    multi_instance_unsafe_dependencies,
)
from cloud.object_storage import get_object_store
from cloud.ops_snapshot import admin_token_state, build_config_snapshot
from apps.core.runtime_registry import get_runtime_error
from aiagent.perception.voice_call_store import voice_call_store

_CALL_STORE = voice_call_store

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
    # Redis 相关检查标注失败策略：fail_open / fail_closed / fallback_memory / ignore。
    failure_mode: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ReadinessSnapshot(BaseModel):
    ok: bool
    status: ReadinessStatus
    checks: dict[str, bool]
    summary: dict[str, int]
    items: list[ReadinessCheck]
    cloud_mode: bool
    # "public" = /ready，只回可用性信号；"ops" = /cloud/ops/readiness，含完整细节。
    purpose: str = "public"
    details: dict[str, Any] = Field(default_factory=dict)


async def build_public_readiness() -> ReadinessSnapshot:
    redis = await redis_health()
    gpu = await gpu_client.health_all()
    voice_store = await voice_call_store.backend_status()

    items = [
        _runtime_import_check(),
        _redis_check(redis),
        _storage_provider_check(),
        _gpu_check("gpu_llm", gpu.get("llm", {}), required=cloud_settings.cloud_mode),
        _gpu_check("gpu_tts", gpu.get("tts", {}), required=False),
        _gpu_check("gpu_asr", gpu.get("asr", {}), required=False),
        _voice_call_store_check(voice_store),
        _gpu_circuit_check(gpu),
    ]

    return _snapshot(
        items=items,
        purpose="public",
        details={
            "redis": redis,
            "gpu": gpu,
            "voice_call_store": voice_store,
        },
    )


async def build_ops_readiness(task_queue: CloudTaskQueue | None = None) -> ReadinessSnapshot:
    redis = await redis_health()
    gpu = await gpu_client.health_all()
    voice_store = await voice_call_store.backend_status()
    config_snapshot = build_config_snapshot()
    risk_summary = config_snapshot["risk_summary"]

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
        _cloud_config_risk_check(risk_summary),
        _gpu_check("gpu_llm", gpu.get("llm", {}), required=cloud_settings.cloud_mode),
        _gpu_check("gpu_tts", gpu.get("tts", {}), required=False),
        _gpu_check("gpu_asr", gpu.get("asr", {}), required=False),
        _gpu_circuit_check(gpu),
        _redis_failure_policy_check(),
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
            "risk_summary": risk_summary,
            "redis_failure_policy": describe_failure_policy(),
        },
        purpose="ops",
    )


def _snapshot(
    *,
    items: list[ReadinessCheck],
    details: dict[str, Any],
    purpose: str = "public",
) -> ReadinessSnapshot:
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
        purpose=purpose,
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

    describe: dict[str, Any] = {}
    if ok:
        try:
            describe = get_object_store().describe()
        except Exception as exc:
            describe = {"error": str(exc)}

    return ReadinessCheck(
        name="storage_provider",
        ok=ok,
        required=True,
        summary="Storage provider is supported." if ok else "Storage provider is unsupported.",
        action="" if ok else "将 STORAGE_PROVIDER 配置为 local、cos 或 s3。",
        details={"provider": cloud_settings.storage_provider, "describe": describe},
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
    state = admin_token_state()
    configured = bool(state["configured"])
    strong = bool(state["strong"])
    ok = strong if required else True

    if strong:
        summary = "Cloud admin token is configured."
        action = ""
    elif configured:
        summary = "Cloud admin token is configured but weak."
        action = "请将 CLOUD_ADMIN_TOKEN 替换为强随机值，避免 change-*、your-*、example、unit-token 等占位符。"
    else:
        summary = "Cloud admin token is missing."
        action = "配置 CLOUD_ADMIN_TOKEN，避免管理接口无法安全访问。"

    return ReadinessCheck(
        name="cloud_admin_token",
        ok=ok,
        required=required,
        summary=summary,
        action=action,
        details=state,
    )

def _cloud_config_risk_check(risk_summary: dict[str, Any]) -> ReadinessCheck:
    critical = int(risk_summary.get("critical") or 0)
    high = int(risk_summary.get("high") or 0)
    count = int(risk_summary.get("count") or 0)

    ok = critical == 0

    if critical:
        summary = f"Cloud config has {critical} critical risk(s)."
        action = "先修复 critical 配置风险，再允许云环境接收生产流量。"
    elif high:
        summary = f"Cloud config has {high} high risk warning(s)."
        action = "建议在发布前修复 high 级别配置风险。"
    else:
        summary = "Cloud config risk check passed."
        action = ""

    return ReadinessCheck(
        name="cloud_config_risk",
        ok=ok,
        required=True,
        summary=summary,
        action=action,
        details={
            "count": count,
            "critical": critical,
            "high": high,
            "items": risk_summary.get("items") or [],
        },
    )

def _voice_call_store_check(
    state: dict[str, Any],
) -> ReadinessCheck:
    effective_provider = str(
        state.get("effective_provider") or "unknown"
    )
    configured_provider = str(
        state.get("configured_provider") or "auto"
    )

    redis_expected = configured_provider == "redis" or (
        configured_provider == "auto"
        and bool(cloud_settings.redis_url)
    )
    required = bool(
        cloud_settings.cloud_mode
        or redis_expected
    )
    ok = bool(state.get("ok", False))

    if ok and effective_provider == "redis":
        summary = "Voice call store is using Redis."
        action = ""
    elif ok and effective_provider == "memory":
        summary = "Voice call store is using process memory."
        action = ""
    elif ok and effective_provider == "memory_fallback":
        summary = "Voice call store is using memory fallback."
        action = (
            "检查 Redis；多实例环境下 memory fallback "
            "不能保证通话状态一致。"
        )
    else:
        summary = "Voice call store is unavailable."
        action = (
            "检查 REDIS_URL、Redis 网络和 "
            "VOICE_CALL_STORE_PROVIDER 配置。"
        )

    return ReadinessCheck(
        name="voice_call_store",
        ok=ok,
        required=required,
        summary=summary,
        action=action,
        failure_mode=FailureMode.FALLBACK_MEMORY.value,
        details=state,
    )


def _gpu_circuit_check(gpu: dict[str, Any]) -> ReadinessCheck:
    """GPU 熔断状态：服务 health 通过但熔断器已打开，也必须算降级。"""
    circuits = gpu.get("circuit") or {}
    open_names = [
        name for name, item in circuits.items()
        if str(item.get("state") or "") == "open"
    ]

    return ReadinessCheck(
        name="gpu_circuit",
        ok=not open_names,
        required=False,
        summary=(
            "All GPU circuit breakers are closed."
            if not open_names
            else f"GPU circuit breakers open: {', '.join(sorted(open_names))}"
        ),
        action="" if not open_names else "检查对应 GPU 服务健康状态；熔断器会在恢复窗口后自动半开重试。",
        failure_mode=FailureMode.FAIL_CLOSED.value,
        details={"open_circuits": sorted(open_names), "circuits": circuits},
    )


def _redis_failure_policy_check() -> ReadinessCheck:
    unsafe = multi_instance_unsafe_dependencies()

    return ReadinessCheck(
        name="redis_failure_policy",
        ok=True,
        required=False,
        summary="Redis failure policy is declared for every dependency.",
        action=(
            f"多实例部署时注意：{', '.join(unsafe)} 在 Redis 不可用时会退化为单进程内存。"
            if unsafe else ""
        ),
        details={
            "policy": describe_failure_policy(),
            "multi_instance_unsafe": unsafe,
        },
    )


def redact_snapshot(snapshot: ReadinessSnapshot) -> ReadinessSnapshot:
    """公共就绪端点专用：去掉所有内部细节，只保留可用性信号。"""
    return ReadinessSnapshot(
        ok=snapshot.ok,
        status=snapshot.status,
        checks=dict(snapshot.checks),
        summary=dict(snapshot.summary),
        items=[
            ReadinessCheck(
                name=item.name,
                ok=item.ok,
                required=item.required,
                summary=item.summary,
            )
            for item in snapshot.items
        ],
        cloud_mode=snapshot.cloud_mode,
        purpose=snapshot.purpose,
        details={},
    )