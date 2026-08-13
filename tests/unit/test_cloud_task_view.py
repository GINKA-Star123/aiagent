from cloud.task_view import (
    normalize_timestamp,
    sanitize_task,
    sanitize_value,
    task_duration_ms,
    task_latency_ms,
)


def test_sanitize_value_redacts_sensitive_keys():
    value = {
        "api_key": "sk-secret",
        "nested": {
            "access_token": "token-value",
            "safe": "hello",
        },
    }

    result = sanitize_value(value)

    assert result["api_key"] == "[redacted]"
    assert result["nested"]["access_token"] == "[redacted]"
    assert result["nested"]["safe"] == "hello"


def test_sanitize_task_normalizes_core_fields():
    task = {
        "id": "t1",
        "type": "knowledge.rebuild",
        "queue": "default",
        "status": "running",
        "payload": {"force_rebuild": True, "token": "secret"},
        "result": None,
        "error": "",
        "created_at": "1000",
        "started_at": "1001",
        "finished_at": "1002",
        "attempts": "1",
        "max_attempts": "3",
    }

    result = sanitize_task(task)

    assert result["id"] == "t1"
    assert result["payload"]["token"] == "[redacted]"
    assert result["attempts"] == 1
    assert result["max_attempts"] == 3
    assert result["duration_ms"] == 1000.0
    assert result["latency_ms"] == 1000.0
    assert result["retryable"] is False


def test_sanitize_task_exposes_dead_letter_fields():
    task = {
        "id": "t2",
        "type": "vision.characters.rebuild",
        "queue": "default",
        "status": "dead",
        "payload": {"force_rebuild": True},
        "result": None,
        "error": "failed token=secret-value password:secret-password",
        "last_error": "failed api_key=secret-key",
        "dead_reason": "max_attempts_exhausted",
        "created_at": "1000",
        "started_at": "1001",
        "last_failed_at": "1003",
        "last_attempt_started_at": "1001",
        "last_attempt_finished_at": "1003",
        "finished_at": "1003",
        "updated_at": "1003",
        "manual_retry_at": "",
        "attempts": "3",
        "max_attempts": "3",
        "worker_id": "worker-1",
    }

    result = sanitize_task(task)

    assert result["status"] == "dead"
    assert result["retryable"] is True
    assert result["dead_reason"] == "max_attempts_exhausted"
    assert "secret-value" not in result["error"]
    assert "secret-password" not in result["error"]
    assert "secret-key" not in result["last_error"]
    assert result["duration_ms"] == 2000.0
    assert result["worker_id"] == "worker-1"


def test_normalize_timestamp_accepts_empty_value():
    assert normalize_timestamp("") == ""
    assert normalize_timestamp(None) == ""


def test_task_duration_ms_uses_explicit_duration_first():
    assert task_duration_ms({"duration_ms": "12.34"}) == 12.34


def test_task_latency_ms_keeps_backward_compatibility():
    assert task_latency_ms({"started_at": "1001", "finished_at": "1002"}) == 1000.0


def test_task_duration_ms_returns_zero_for_missing_times():
    assert task_duration_ms({"started_at": "", "finished_at": ""}) == 0.0