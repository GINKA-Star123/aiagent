from __future__ import annotations

from cloud.failure_policy import (
    FailureMode,
    RedisDependency,
    describe_failure_policy,
    failure_mode_for,
    failure_reason_for,
    multi_instance_unsafe_dependencies,
)


def test_rate_limit_and_concurrency_fail_open():
    assert failure_mode_for(RedisDependency.RATE_LIMIT) == FailureMode.FAIL_OPEN
    assert failure_mode_for("concurrency_limit") == FailureMode.FAIL_OPEN


def test_task_queue_and_lock_fail_closed():
    assert failure_mode_for(RedisDependency.TASK_QUEUE) == FailureMode.FAIL_CLOSED
    assert failure_mode_for("unique_lock") == FailureMode.FAIL_CLOSED


def test_voice_call_store_falls_back_to_memory():
    assert failure_mode_for(RedisDependency.VOICE_CALL_STORE) == FailureMode.FALLBACK_MEMORY
    assert RedisDependency.VOICE_CALL_STORE.value in multi_instance_unsafe_dependencies()
    assert failure_reason_for(RedisDependency.VOICE_CALL_STORE)


def test_unknown_dependency_is_fail_open_and_described():
    assert failure_mode_for("not_registered") == FailureMode.FAIL_OPEN

    table = describe_failure_policy()
    assert {item["dependency"] for item in table} == {
        dependency.value for dependency in RedisDependency
    }
    assert all(item["failure_mode"] and item["reason"] for item in table)
