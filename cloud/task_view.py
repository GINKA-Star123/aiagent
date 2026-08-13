from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

SENSITIVE_KEY_PARTS = {
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "access_key",
    "private_key",
}

SECRET_ASSIGNMENT_PATTERNS = [
    re.compile(
        r"(?i)\b(token|api[_-]?key|secret|password|authorization)\b\s*[:=]\s*[^\s,;]+"
    ),
]


def sanitize_task(task: dict[str, Any], *, max_error_chars: int = 1600) -> dict[str, Any]:
    status = str(task.get("status") or "unknown")

    return {
        "id": str(task.get("id") or ""),
        "type": str(task.get("type") or ""),
        "queue": str(task.get("queue") or "default"),
        "status": status,
        "payload": sanitize_value(task.get("payload")),
        "result": sanitize_value(task.get("result")),
        "error": sanitize_text(str(task.get("error") or ""), max_error_chars),
        "last_error": sanitize_text(str(task.get("last_error") or ""), max_error_chars),
        "unique_key": str(task.get("unique_key") or ""),
        "created_at": normalize_timestamp(task.get("created_at")),
        "started_at": normalize_timestamp(task.get("started_at")),
        "finished_at": normalize_timestamp(task.get("finished_at")),
        "updated_at": normalize_timestamp(task.get("updated_at")),
        "last_failed_at": normalize_timestamp(task.get("last_failed_at")),
        "last_attempt_started_at": normalize_timestamp(
            task.get("last_attempt_started_at")
        ),
        "last_attempt_finished_at": normalize_timestamp(
            task.get("last_attempt_finished_at")
        ),
        "manual_retry_at": normalize_timestamp(task.get("manual_retry_at")),
        "worker_id": str(task.get("worker_id") or ""),
        "attempts": _safe_int(task.get("attempts"), 0),
        "max_attempts": _safe_int(task.get("max_attempts"), 0),
        "dead_reason": str(task.get("dead_reason") or ""),
        "duration_ms": task_duration_ms(task),
        "latency_ms": task_duration_ms(task),
        "age_seconds": task_age_seconds(task),
        "retryable": status == "dead",
    }


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                output[key_text] = "[redacted]"
            else:
                output[key_text] = sanitize_value(item)
        return output

    if isinstance(value, list):
        return [sanitize_value(item) for item in value]

    if isinstance(value, str):
        return sanitize_text(value, 1600)

    return value


def sanitize_text(value: str, max_chars: int = 1600) -> str:
    text = value

    for pattern in SECRET_ASSIGNMENT_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}=[redacted]", text)

    return _truncate(text, max_chars)


def normalize_timestamp(value: Any) -> str:
    if value in {None, ""}:
        return ""

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value)).isoformat(timespec="seconds")

    text = str(value).strip()
    if not text:
        return ""

    try:
        return datetime.fromtimestamp(float(text)).isoformat(timespec="seconds")
    except Exception:
        return text


def task_duration_ms(task: dict[str, Any]) -> float:
    explicit = _safe_float(task.get("duration_ms"), 0.0)
    if explicit > 0:
        return round(explicit, 2)

    started = _timestamp_seconds(
        task.get("last_attempt_started_at") or task.get("started_at")
    )
    finished = _timestamp_seconds(
        task.get("last_attempt_finished_at") or task.get("finished_at")
    )

    if not started or not finished or finished < started:
        return 0.0

    return round((finished - started) * 1000, 2)


def task_latency_ms(task: dict[str, Any]) -> float:
    return task_duration_ms(task)


def task_age_seconds(task: dict[str, Any]) -> float:
    created = _timestamp_seconds(task.get("created_at"))
    if not created:
        return 0.0
    return round(time.time() - created, 2)


def _timestamp_seconds(value: Any) -> float:
    if value in {None, ""}:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    try:
        return float(text)
    except Exception:
        pass

    try:
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "...[truncated]"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)