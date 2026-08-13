import asyncio

import pytest

from cloud.task_queue import CloudTaskQueue, _memory_store


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def reset_memory_task_store(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "")

    async with _memory_store.lock:
        _memory_store.tasks.clear()
        _memory_store.unique.clear()
        _memory_store.queue = asyncio.Queue()

    yield

    async with _memory_store.lock:
        _memory_store.tasks.clear()
        _memory_store.unique.clear()
        _memory_store.queue = asyncio.Queue()


@pytest.mark.anyio
async def test_enqueue_unique_key_returns_existing_task():
    queue = CloudTaskQueue(prefix="unit")

    first = await queue.enqueue(
        "knowledge.rebuild",
        payload={"force_rebuild": True},
        unique_key="knowledge.rebuild",
    )
    second = await queue.enqueue(
        "knowledge.rebuild",
        payload={"force_rebuild": True},
        unique_key="knowledge.rebuild",
    )

    assert first.created is True
    assert second.created is False
    assert second.task_id == first.task_id
    assert second.status == "queued"


@pytest.mark.anyio
async def test_fail_or_retry_records_retry_observability_fields():
    queue = CloudTaskQueue(prefix="unit")

    submitted = await queue.enqueue(
        "unit.task",
        payload={"safe": "value"},
        max_attempts=2,
    )

    task = await queue.pop(timeout_seconds=1)
    assert task is not None

    await queue.start(submitted.task_id, "worker-1")
    result = await queue.fail_or_retry(
        submitted.task_id,
        error="temporary failure token=secret",
    )

    latest = await queue.get(submitted.task_id)

    assert result.retried is True
    assert result.dead is False
    assert result.status == "queued"
    assert result.attempts == 1
    assert result.max_attempts == 2

    assert latest["status"] == "queued"
    assert latest["error"] == "temporary failure token=secret"
    assert latest["last_error"] == "temporary failure token=secret"
    assert latest["last_failed_at"]
    assert latest["last_attempt_finished_at"]
    assert latest["duration_ms"] >= 0


@pytest.mark.anyio
async def test_fail_or_retry_moves_task_to_dead_letter_after_max_attempts():
    queue = CloudTaskQueue(prefix="unit")

    submitted = await queue.enqueue(
        "unit.task",
        payload={"safe": "value"},
        max_attempts=1,
    )

    task = await queue.pop(timeout_seconds=1)
    assert task is not None

    await queue.start(submitted.task_id, "worker-1")
    result = await queue.fail_or_retry(
        submitted.task_id,
        error="fatal failure",
    )

    latest = await queue.get(submitted.task_id)
    dead_tasks = await queue.list_dead_tasks()

    assert result.retried is False
    assert result.dead is True
    assert result.status == "dead"
    assert result.dead_reason == "max_attempts_exhausted"

    assert latest["status"] == "dead"
    assert latest["dead_reason"] == "max_attempts_exhausted"
    assert latest["last_error"] == "fatal failure"
    assert len(dead_tasks) == 1
    assert dead_tasks[0]["id"] == submitted.task_id


@pytest.mark.anyio
async def test_retry_dead_task_requeues_and_grants_one_more_attempt():
    queue = CloudTaskQueue(prefix="unit")

    submitted = await queue.enqueue(
        "unit.task",
        payload={"safe": "value"},
        max_attempts=1,
    )

    task = await queue.pop(timeout_seconds=1)
    assert task is not None

    await queue.start(submitted.task_id, "worker-1")
    await queue.fail_or_retry(submitted.task_id, error="fatal failure")

    retried = await queue.retry_dead_task(submitted.task_id)
    latest = await queue.get(submitted.task_id)
    summary = await queue.task_summary()

    assert retried is True
    assert latest["status"] == "queued"
    assert latest["error"] == ""
    assert latest["dead_reason"] == ""
    assert latest["manual_retry_at"]
    assert latest["max_attempts"] == 2

    assert summary["queued"] == 1
    assert summary["dead"] == 0
    assert summary["retryable"] == 0
    assert summary["queue_depth"] == 1


@pytest.mark.anyio
async def test_finish_records_result_and_duration():
    queue = CloudTaskQueue(prefix="unit")

    submitted = await queue.enqueue(
        "unit.task",
        payload={"safe": "value"},
    )

    task = await queue.pop(timeout_seconds=1)
    assert task is not None

    await queue.start(submitted.task_id, "worker-1")
    await queue.finish(submitted.task_id, {"ok": True})

    latest = await queue.get(submitted.task_id)

    assert latest["status"] == "succeeded"
    assert latest["result"] == {"ok": True}
    assert latest["finished_at"]
    assert latest["last_attempt_finished_at"]
    assert latest["duration_ms"] >= 0