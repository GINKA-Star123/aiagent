from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def now_perf() -> float:
    return time.perf_counter()


def elapsed_ms(started_at: float) -> str:
    return f"{(now_perf() - started_at) * 1000:.2f}"


def metadata_set(
    metadata: dict[str, Any] | None,
    **items: Any,
) -> dict[str, Any]:
    next_metadata = dict(metadata or {})
    for key, value in items.items():
        next_metadata[str(key)] = value

    return next_metadata


def metadata_strings(metadata: dict[str, Any] | None) -> dict[str, str]:
    return {
        str(key): _stringify_metadata_value(value)
        for key, value in dict(metadata or {}).items()
    }


def mark_stage_started(
    metadata: dict[str, Any] | None,
    stage: str,
) -> dict[str, Any]:
    return metadata_set(
        metadata,
        **{
            f"{stage}_status": "started",
        },
    )


def mark_stage_done(
    metadata: dict[str, Any] | None,
    stage: str,
    started_at: float,
    **extra: Any,
) -> dict[str, Any]:
    return metadata_set(
        metadata,
        **{
            f"{stage}_status": "done",
            f"{stage}_latency_ms": elapsed_ms(started_at),
            **extra,
        },
    )


def mark_stage_skipped(
    metadata: dict[str, Any] | None,
    stage: str,
    reason: str,
    **extra: Any,
) -> dict[str, Any]:
    return metadata_set(
        metadata,
        **{
            f"{stage}_status": "skipped",
            f"{stage}_skip_reason": reason,
            **extra,
        },
    )


def mark_stage_failed(
    metadata: dict[str, Any] | None,
    stage: str,
    started_at: float,
    error: Exception | str,
    **extra: Any,
) -> dict[str, Any]:
    return metadata_set(
        metadata,
        **{
            f"{stage}_status": "failed",
            f"{stage}_latency_ms": elapsed_ms(started_at),
            f"{stage}_error": str(error),
            **extra,
        },
    )


def run_stage(
    *,
    metadata: dict[str, Any] | None,
    stage: str,
    fn: Callable[[], T],
) -> tuple[T, dict[str, Any]]:
    started_at = now_perf()
    try:
        result = fn()
    except Exception as exc:
        raise StageExecutionError(
            stage=stage,
            metadata=mark_stage_failed(metadata, stage, started_at, exc),
            original=exc,
        ) from exc

    return result, mark_stage_done(metadata, stage, started_at)


class StageExecutionError(RuntimeError):
    def __init__(
        self,
        *,
        stage: str,
        metadata: dict[str, Any],
        original: Exception,
    ) -> None:
        super().__init__(str(original))
        self.stage = stage
        self.metadata = metadata
        self.original = original


def _stringify_metadata_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    return str(value)
