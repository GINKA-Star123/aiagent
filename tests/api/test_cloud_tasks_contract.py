import asyncio

from apps.api.routes.cloud_tasks import task_queue
from cloud.task_queue import _memory_store
from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
    assert_ok_response,
)


def _admin_headers(monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-admin-token-strong-123456")
    return {"x-cloud-admin-token": "unit-admin-token-strong-123456"}


def _reset_memory_store():
    _memory_store.tasks.clear()
    _memory_store.unique.clear()
    _memory_store.queue = asyncio.Queue()


async def _enqueue_unit_task() -> str:
    result = await task_queue.enqueue(
        "unit.task",
        payload={"api_key": "secret", "safe": "value"},
        max_attempts=3,
    )
    return result.task_id


async def _create_dead_task() -> str:
    result = await task_queue.enqueue(
        "unit.task",
        payload={"token": "secret"},
        max_attempts=1,
    )
    task = await task_queue.pop(timeout_seconds=1)
    assert task is not None

    await task_queue.start(result.task_id, "api-test-worker")
    await task_queue.fail_or_retry(
        result.task_id,
        error="unit failure token=secret",
    )
    return result.task_id


def test_cloud_tasks_summary_requires_admin_token(api_client):
    response = api_client.get("/cloud/tasks/summary")
    data = assert_json_response(response, expected_status=503)

    assert_error_response(data, stage="cloud_admin_auth")


def test_cloud_tasks_summary_accepts_cloud_admin_header(api_client, monkeypatch):
    _reset_memory_store()
    headers = _admin_headers(monkeypatch)

    response = api_client.get(
        "/cloud/tasks/summary",
        headers=headers,
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["queue"] == "default"
    assert "generated_at" in data
    assert "summary" in data
    assert isinstance(data["summary"], dict)
    assert "queue_depth" in data["summary"]
    assert "dead_depth" in data["summary"]


def test_cloud_tasks_list_contract(api_client, monkeypatch):
    _reset_memory_store()
    headers = _admin_headers(monkeypatch)
    task_id = asyncio.run(_enqueue_unit_task())

    response = api_client.get(
        "/cloud/tasks",
        headers=headers,
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["queue"] == "default"
    assert data["limit"] == 50
    assert "generated_at" in data
    assert isinstance(data["tasks"], list)

    task = next(item for item in data["tasks"] if item["id"] == task_id)
    assert task["status"] == "queued"
    assert task["payload"]["api_key"] == "[redacted]"
    assert "duration_ms" in task
    assert "age_seconds" in task
    assert task["retryable"] is False


def test_cloud_task_get_missing_contract(api_client, monkeypatch):
    headers = _admin_headers(monkeypatch)

    response = api_client.get(
        "/cloud/tasks/missing-task-id",
        headers=headers,
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="cloud_task_get")
    assert data["task_id"] == "missing-task-id"


def test_cloud_task_get_contract(api_client, monkeypatch):
    _reset_memory_store()
    headers = _admin_headers(monkeypatch)
    task_id = asyncio.run(_enqueue_unit_task())

    response = api_client.get(
        f"/cloud/tasks/{task_id}",
        headers=headers,
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["task"]["id"] == task_id
    assert data["task"]["status"] == "queued"
    assert data["task"]["payload"]["api_key"] == "[redacted]"


def test_cloud_task_dead_letter_contract(api_client, monkeypatch):
    _reset_memory_store()
    headers = _admin_headers(monkeypatch)
    task_id = asyncio.run(_enqueue_unit_task())

    response = api_client.post(
        f"/cloud/tasks/{task_id}/dead-letter",
        headers=headers,
        json={
            "reason": "unit_manual_dead_letter",
            "error": "manual failure token=secret",
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["task_id"] == task_id
    assert data["status"] == "dead"
    assert data["dead_lettered"] is True
    assert data["task"]["status"] == "dead"
    assert data["task"]["dead_reason"] == "unit_manual_dead_letter"
    assert "secret" not in data["task"]["error"]


def test_cloud_tasks_dead_list_contract(api_client, monkeypatch):
    _reset_memory_store()
    headers = _admin_headers(monkeypatch)
    task_id = asyncio.run(_create_dead_task())

    response = api_client.get(
        "/cloud/tasks/dead",
        headers=headers,
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["queue"] == "default"
    assert isinstance(data["tasks"], list)

    task = next(item for item in data["tasks"] if item["id"] == task_id)
    assert task["status"] == "dead"
    assert task["retryable"] is True
    assert task["dead_reason"] == "max_attempts_exhausted"
    assert "secret" not in task["error"]


def test_cloud_task_retry_missing_contract(api_client, monkeypatch):
    headers = _admin_headers(monkeypatch)

    response = api_client.post(
        "/cloud/tasks/missing-task-id/retry",
        headers=headers,
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="cloud_task_retry")
    assert data["task_id"] == "missing-task-id"


def test_cloud_task_retry_dead_task_contract(api_client, monkeypatch):
    _reset_memory_store()
    headers = _admin_headers(monkeypatch)
    task_id = asyncio.run(_create_dead_task())

    response = api_client.post(
        f"/cloud/tasks/{task_id}/retry",
        headers=headers,
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["task_id"] == task_id
    assert data["status"] == "queued"
    assert data["retried"] is True
    assert data["task"]["status"] == "queued"
    assert data["task"]["retryable"] is False
    assert data["task"]["dead_reason"] == ""
    assert data["task"]["max_attempts"] == 2
