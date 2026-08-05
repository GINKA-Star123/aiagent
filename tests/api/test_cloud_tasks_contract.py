from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
    assert_ok_response,
)


def test_cloud_tasks_summary_requires_admin_token(api_client):
    response = api_client.get("/cloud/tasks/summary")
    data = assert_json_response(response, expected_status=503)

    assert_error_response(data, stage="cloud_admin_auth")


def test_cloud_tasks_summary_accepts_cloud_admin_header(api_client, monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    response = api_client.get(
        "/cloud/tasks/summary",
        headers={"x-cloud-admin-token": "unit-token"},
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["queue"] == "default"
    assert "summary" in data
    assert isinstance(data["summary"], dict)


def test_cloud_task_get_missing_contract(api_client, monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    response = api_client.get(
        "/cloud/tasks/missing-task-id",
        headers={"x-cloud-admin-token": "unit-token"},
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="cloud_task_get")
    assert data["task_id"] == "missing-task-id"


def test_cloud_task_retry_missing_contract(api_client, monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    response = api_client.post(
        "/cloud/tasks/missing-task-id/retry",
        headers={"x-cloud-admin-token": "unit-token"},
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="cloud_task_retry")
    assert data["task_id"] == "missing-task-id"