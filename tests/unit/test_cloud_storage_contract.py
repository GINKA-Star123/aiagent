from __future__ import annotations

from pathlib import Path

from apps.api.routes import cloud as cloud_route
from cloud.config import cloud_settings
from cloud.object_storage import reset_object_store_for_tests
from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
    assert_ok_response,
)


def test_cloud_ready_contract(api_client):
    response = api_client.get("/cloud/ready")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "cloud_mode" in data
    assert "region" in data
    assert "redis" in data
    assert "storage" in data
    assert "gpu" in data

    assert "provider" in data["storage"]
    assert "bucket_configured" in data["storage"]


def test_cloud_limits_contract(api_client):
    response = api_client.get("/cloud/limits")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "rate_limit_enabled" in data
    assert "inflight_limit_enabled" in data
    assert "limits" in data

    limits = data["limits"]

    for field in [
        "global_inflight",
        "chat_inflight",
        "multimodal_inflight",
        "voice_inflight",
        "rebuild_inflight",
        "chat_per_minute",
        "multimodal_per_minute",
        "voice_per_minute",
        "rebuild_per_minute",
    ]:
        assert field in limits


def test_direct_upload_contract(api_client, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        cloud_settings,
        "local_storage_root",
        str(tmp_path),
    )
    monkeypatch.setattr(
        cloud_settings,
        "storage_provider",
        "local",
    )
    monkeypatch.setattr(
        cloud_settings,
        "api_public_base_url",
        "",
    )

    reset_object_store_for_tests()

    response = api_client.post(
        "/cloud/storage/upload",
        data={"prefix": "contract-tests"},
        files={
            "file": (
                "hello.txt",
                b"hello cloud storage",
                "text/plain",
            )
        },
    )

    data = assert_json_response(response)

    assert_ok_response(data)
    assert "object" in data

    stored = data["object"]

    assert stored["provider"] == "local"
    assert stored["size"] == len(b"hello cloud storage")
    assert stored["content_type"] == "text/plain"
    assert stored["key"].startswith("contract-tests/")
    assert stored["url"].startswith("/cloud-files/")

    stored_path = tmp_path / stored["key"]
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"hello cloud storage"

    reset_object_store_for_tests()


def test_direct_upload_size_limit_contract(
    api_client,
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        cloud_settings,
        "local_storage_root",
        str(tmp_path),
    )
    monkeypatch.setattr(
        cloud_settings,
        "storage_provider",
        "local",
    )
    monkeypatch.setattr(
        cloud_settings,
        "upload_max_bytes",
        4,
    )

    reset_object_store_for_tests()

    response = api_client.post(
        "/cloud/storage/upload",
        files={
            "file": (
                "too-large.txt",
                b"12345",
                "text/plain",
            )
        },
    )

    data = assert_json_response(response, expected_status=413)

    assert_error_response(
        data,
        stage="upload_size_limit",
    )
    assert data["max_bytes"] == 4
    assert data["actual_bytes"] == 5

    reset_object_store_for_tests()


def test_presign_upload_is_unsupported_for_local_storage(
    api_client,
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        cloud_settings,
        "storage_provider",
        "local",
    )
    monkeypatch.setattr(
        cloud_settings,
        "local_storage_root",
        str(tmp_path),
    )

    reset_object_store_for_tests()

    response = api_client.post(
        "/cloud/storage/presign-upload",
        json={
            "filename": "avatar.png",
            "content_type": "image/png",
            "prefix": "contract-tests",
            "expires_seconds": 900,
        },
    )

    data = assert_json_response(response, expected_status=400)

    assert_error_response(
        data,
        stage="object_storage_unsupported",
    )
    assert "presigned upload" in data["error"]

    reset_object_store_for_tests()


def test_presign_upload_validation_contract(api_client):
    response = api_client.post(
        "/cloud/storage/presign-upload",
        json={
            "filename": "",
            "content_type": "image/png",
            "prefix": "uploads",
            "expires_seconds": 900,
        },
    )

    data = assert_json_response(response, expected_status=422)

    assert data["ok"] is False
    assert data["stage"] == "cloud_validation"
    assert isinstance(data["error"], str)
    assert isinstance(data.get("request_id", ""), str)