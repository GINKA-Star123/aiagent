from __future__ import annotations

from enum import StrEnum
from typing import Any


class RedisDependency(StrEnum):
    """依赖 Redis 的能力清单。新增 Redis 依赖时必须在这里登记。"""

    RATE_LIMIT = "rate_limit"
    CONCURRENCY_LIMIT = "concurrency_limit"
    TASK_QUEUE = "task_queue"
    UNIQUE_LOCK = "unique_lock"
    VOICE_CALL_STORE = "voice_call_store"
    METRICS_STORE = "metrics_store"


class FailureMode(StrEnum):
    """Redis 不可用时的处理方式。"""

    FAIL_OPEN = "fail_open"
    FAIL_CLOSED = "fail_closed"
    FALLBACK_MEMORY = "fallback_memory"
    IGNORE = "ignore"


# 每个依赖的失败策略：按"正确性 vs 可用性"取舍，而不是一刀切。
REDIS_FAILURE_POLICY: dict[RedisDependency, FailureMode] = {
    # 限流/并发：放行最多是多打一点流量，拒绝会直接伤害正常用户。
    RedisDependency.RATE_LIMIT: FailureMode.FAIL_OPEN,
    RedisDependency.CONCURRENCY_LIMIT: FailureMode.FAIL_OPEN,
    # 任务队列/唯一锁：重复执行重建任务会破坏数据一致性，必须拒绝。
    RedisDependency.TASK_QUEUE: FailureMode.FAIL_CLOSED,
    RedisDependency.UNIQUE_LOCK: FailureMode.FAIL_CLOSED,
    # 通话状态：可以退化成单进程内存，但多实例下必须告警。
    RedisDependency.VOICE_CALL_STORE: FailureMode.FALLBACK_MEMORY,
    # 指标：只影响可观测性。
    RedisDependency.METRICS_STORE: FailureMode.IGNORE,
}

FAILURE_MODE_REASONS: dict[FailureMode, str] = {
    FailureMode.FAIL_OPEN: "宁可放宽限流也不能拒绝正常用户。",
    FailureMode.FAIL_CLOSED: "宁可拒绝任务也不能重复执行破坏一致性。",
    FailureMode.FALLBACK_MEMORY: "退化为单进程内存；多实例部署下状态可能不一致，需要告警。",
    FailureMode.IGNORE: "仅影响可观测性，不影响主链路。",
}

# 这些模式在多实例部署下不安全，readiness / diagnostics 会据此给出告警。
MULTI_INSTANCE_UNSAFE_MODES = {
    FailureMode.FALLBACK_MEMORY,
}


def failure_mode_for(dependency: RedisDependency | str) -> FailureMode:
    key = _dependency(dependency)
    return REDIS_FAILURE_POLICY.get(key, FailureMode.FAIL_OPEN)


def failure_reason_for(dependency: RedisDependency | str) -> str:
    return FAILURE_MODE_REASONS.get(failure_mode_for(dependency), "")


def multi_instance_unsafe_dependencies() -> list[str]:
    return [
        dependency.value
        for dependency, mode in REDIS_FAILURE_POLICY.items()
        if mode in MULTI_INSTANCE_UNSAFE_MODES
    ]


def describe_failure_policy() -> list[dict[str, Any]]:
    """供 /cloud/ops/readiness 与 diagnostics 展示的策略表。"""
    return [
        {
            "dependency": dependency.value,
            "failure_mode": mode.value,
            "reason": FAILURE_MODE_REASONS.get(mode, ""),
        }
        for dependency, mode in REDIS_FAILURE_POLICY.items()
    ]


def _dependency(value: RedisDependency | str) -> RedisDependency:
    if isinstance(value, RedisDependency):
        return value
    try:
        return RedisDependency(str(value).strip().lower())
    except Exception:
        return RedisDependency.RATE_LIMIT