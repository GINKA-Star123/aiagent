from __future__ import annotations

from tests.helpers.api_contract import (
    assert_chat_response_contract,
    assert_json_response,
    assert_ok_response,
)


def test_health_contract(api_client):
    response = api_client.get("/health")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data.get("status") == "ok"
    assert "cloud_mode" in data


def test_ready_contract(api_client):
    response = api_client.get("/ready")
    data = assert_json_response(response)

    assert "ok" in data
    assert "status" in data
    assert "checks" in data
    assert isinstance(data["checks"], dict)


def test_runtime_diagnostics_contract(api_client):
    response = api_client.get("/runtime/diagnostics")
    data = assert_json_response(response)

    assert "ok" in data
    assert "status" in data
    assert "checks" in data
    assert "summary" in data
    assert isinstance(data["checks"], list)
    assert isinstance(data["summary"], dict)


def test_runtime_capabilities_contract(api_client):
    response = api_client.get("/runtime/capabilities")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "capabilities" in data

    capabilities = data["capabilities"]
    assert isinstance(capabilities, dict)
    assert "status" in capabilities
    assert "summary" in capabilities
    assert "items" in capabilities


def test_chat_contract(api_client, test_user):
    response = api_client.post(
        "/chat",
        json={
            "user_id": test_user["user_id"],
            "username": test_user["username"],
            "text": "你好",
        },
    )
    data = assert_json_response(response)

    assert_chat_response_contract(data)
    assert data["reply"]


def test_multimodal_chat_contract(api_client, test_user, tiny_png_path):
    with tiny_png_path.open("rb") as file_obj:
        response = api_client.post(
            "/chat/multimodal",
            data={
                "user_id": test_user["user_id"],
                "username": test_user["username"],
                "text": "看看这张图片",
            },
            files={
                "file": ("tiny.png", file_obj, "image/png"),
            },
        )

    data = assert_json_response(response)

    assert_chat_response_contract(data)
