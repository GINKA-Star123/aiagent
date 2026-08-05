from cloud.task_view import normalize_timestamp, sanitize_task, sanitize_value, task_latency_ms


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
    assert result["latency_ms"] == 1000.0


def test_normalize_timestamp_accepts_empty_value():
    assert normalize_timestamp("") == ""
    assert normalize_timestamp(None) == ""


def test_task_latency_ms_returns_zero_for_missing_times():
    assert task_latency_ms({"started_at": "", "finished_at": ""}) == 0.0