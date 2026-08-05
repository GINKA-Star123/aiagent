from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
)


def test_cloud_ops_readiness_requires_admin(api_client):
    response = api_client.get("/cloud/ops/readiness")
    data = assert_json_response(response, expected_status=503)

    assert_error_response(data, stage="cloud_admin_auth")


def test_cloud_ops_readiness_contract(api_client, monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    response = api_client.get(
        "/cloud/ops/readiness",
        headers={"x-cloud-admin-token": "unit-token"},
    )
    data = assert_json_response(response)

    assert "ok" in data
    assert "status" in data
    assert "checks" in data
    assert "items" in data
    assert "summary" in data
    assert "cloud_mode" in data

    assert isinstance(data["checks"], dict)
    assert isinstance(data["items"], list)
    assert isinstance(data["summary"], dict)