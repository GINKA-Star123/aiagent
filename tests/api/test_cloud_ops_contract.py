from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
)


def _admin_headers(monkeypatch, token: str = "unit-admin-token-strong-123456"):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", token)
    return {"x-cloud-admin-token": token}


def test_cloud_ops_readiness_requires_admin(api_client):
    response = api_client.get("/cloud/ops/readiness")
    data = assert_json_response(response, expected_status=503)

    assert_error_response(data, stage="cloud_admin_auth")


def test_cloud_ops_readiness_contract(api_client, monkeypatch):
    headers = _admin_headers(monkeypatch)

    response = api_client.get(
        "/cloud/ops/readiness",
        headers=headers,
    )
    data = assert_json_response(response)

    assert "ok" in data
    assert "status" in data
    assert "checks" in data
    assert "items" in data
    assert "summary" in data
    assert "cloud_mode" in data
    assert "details" in data

    assert isinstance(data["checks"], dict)
    assert isinstance(data["items"], list)
    assert isinstance(data["summary"], dict)
    assert isinstance(data["details"], dict)

    assert "cloud_admin_token" in data["checks"]
    assert "cloud_config_risk" in data["checks"]
    assert "risk_summary" in data["details"]


def test_cloud_ops_readiness_reports_weak_admin_token(api_client, monkeypatch):
    headers = _admin_headers(monkeypatch, token="change-this-admin-token")

    response = api_client.get(
        "/cloud/ops/readiness",
        headers=headers,
    )
    data = assert_json_response(response)

    assert data["checks"]["cloud_admin_token"] is False

    admin_item = next(
        item for item in data["items"]
        if item["name"] == "cloud_admin_token"
    )
    assert admin_item["ok"] is False
    assert admin_item["details"]["configured"] is True
    assert admin_item["details"]["strong"] is False
    assert "placeholder_like" in admin_item["details"]["weak_reasons"]


def test_cloud_ops_config_snapshot_requires_admin(api_client):
    response = api_client.get("/cloud/ops/config-snapshot")
    data = assert_json_response(response, expected_status=503)

    assert_error_response(data, stage="cloud_admin_auth")


def test_cloud_ops_config_snapshot_contract(api_client, monkeypatch):
    headers = _admin_headers(monkeypatch)
    monkeypatch.setenv("GPU_API_TOKEN", "gpu-secret-token")

    response = api_client.get(
        "/cloud/ops/config-snapshot",
        headers=headers,
    )
    data = assert_json_response(response)

    assert data["ok"] is True
    assert "request_id" in data
    assert "cloud" in data
    assert "security" in data
    assert "redis" in data
    assert "storage" in data
    assert "gpu" in data
    assert "limits" in data
    assert "paths" in data
    assert "risk_summary" in data

    assert data["security"]["admin_header"] == "x-cloud-admin-token"
    assert data["security"]["admin_token"]["configured"] is True
    assert data["security"]["admin_token"]["strong"] is True

    assert data["gpu"]["gpu_api_token"]["configured"] is True
    assert data["gpu"]["gpu_api_token"]["redacted"] == "[redacted]"

    assert isinstance(data["risk_summary"]["items"], list)


def test_cloud_ops_config_snapshot_does_not_leak_secret_values(api_client, monkeypatch):
    admin_token = "unit-admin-token-strong-123456"
    headers = _admin_headers(monkeypatch, token=admin_token)
    monkeypatch.setenv("GPU_API_TOKEN", "gpu-secret-token")

    response = api_client.get(
        "/cloud/ops/config-snapshot",
        headers=headers,
    )
    data = assert_json_response(response)
    text = str(data)

    assert admin_token not in text
    assert "gpu-secret-token" not in text
    assert "s3_secret_access_key" in data["storage"]
    assert data["storage"]["s3_secret_access_key"]["configured"] in {True, False}