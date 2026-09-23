from __future__ import annotations

import asyncio

import pytest

from cloud.config import cloud_settings
from cloud.object_storage import (
    LocalObjectStore,
    ObjectStorageUnsupportedError,
    ObjectStorageValidationError,
    StoredObject,
    build_object_key,
    guess_content_type,
    normalize_content_type,
    normalize_expires_seconds,
    normalize_filename,
    normalize_storage_prefix,
    stored_object_payload,
)


def test_normalize_storage_prefix_removes_unsafe_segments():
    value = normalize_storage_prefix("/media/images//avatars/")

    assert value == "media/images/avatars"
    assert ".." not in value
    assert "\\" not in value


def test_normalize_storage_prefix_rejects_parent_segment():
    with pytest.raises(ObjectStorageValidationError):
        normalize_storage_prefix("../private")


def test_normalize_storage_prefix_uses_default_for_empty_value():
    assert normalize_storage_prefix("") == "uploads"
    assert normalize_storage_prefix(None) == "uploads"


def test_normalize_filename_keeps_only_safe_basename():
    value = normalize_filename("../avatar image.png")

    assert value == "avatar_image.png"
    assert "/" not in value
    assert "\\" not in value
    assert ".." not in value


def test_normalize_filename_uses_default_for_empty_value():
    assert normalize_filename("") == "file.bin"
    assert normalize_filename(None) == "file.bin"


def test_normalize_content_type_uses_binary_fallback():
    assert normalize_content_type("") == "application/octet-stream"
    assert normalize_content_type(None) == "application/octet-stream"


def test_normalize_content_type_rejects_invalid_value():
    with pytest.raises(ObjectStorageValidationError):
        normalize_content_type("not-a-content-type")


def test_normalize_expires_seconds_clamps_lower_bound():
    assert normalize_expires_seconds(1) == 60


def test_normalize_expires_seconds_clamps_upper_bound():
    assert normalize_expires_seconds(999999) == 3600


def test_build_object_key_contains_safe_prefix_and_filename():
    key = build_object_key(
        prefix="/uploads/images/",
        filename="../hello world.png",
    )

    assert key.startswith("uploads/images/")
    assert key.endswith("hello_world.png")
    assert ".." not in key
    assert "\\" not in key


def test_guess_content_type_uses_filename_extension():
    assert guess_content_type("voice.mp3") == "audio/mpeg"
    assert guess_content_type("unknown.invalid") == "application/octet-stream"


def test_local_object_store_writes_bytes(tmp_path):
    store = LocalObjectStore(
        root=str(tmp_path),
        public_base_url="",
    )

    stored = asyncio.run(
        store.put_bytes(
            key="uploads/2026/09/file.txt",
            data=b"hello",
            content_type="text/plain",
        )
    )

    assert stored.key == "uploads/2026/09/file.txt"
    assert stored.url == "/cloud-files/uploads/2026/09/file.txt"
    assert stored.size == 5
    assert stored.content_type == "text/plain"
    assert (
        (tmp_path / "uploads" / "2026" / "09" / "file.txt").read_bytes()
        == b"hello"
    )


def test_local_object_store_rejects_path_escape(tmp_path):
    store = LocalObjectStore(
        root=str(tmp_path),
        public_base_url="",
    )

    with pytest.raises(ObjectStorageValidationError):
        asyncio.run(
            store.put_bytes(
                key="../outside.txt",
                data=b"unsafe",
                content_type="text/plain",
            )
        )


def test_local_object_store_does_not_support_presigned_put():
    store = LocalObjectStore(
        root="data/cloud_storage",
        public_base_url="",
    )

    with pytest.raises(ObjectStorageUnsupportedError):
        asyncio.run(
            store.presigned_put_url(
                key="uploads/file.txt",
                content_type="text/plain",
                expires_seconds=900,
            )
        )


def test_local_object_store_presigned_get_returns_public_url(tmp_path):
    store = LocalObjectStore(
        root=str(tmp_path),
        public_base_url="https://api.example.com",
    )

    url = asyncio.run(
        store.presigned_get_url(
            key="uploads/file.txt",
            expires_seconds=900,
        )
    )

    assert url == "https://api.example.com/cloud-files/uploads/file.txt"


def test_stored_object_payload_contains_provider(monkeypatch):
    monkeypatch.setattr(cloud_settings, "storage_provider", "local")

    stored = StoredObject(
        key="uploads/file.txt",
        url="/cloud-files/uploads/file.txt",
        size=10,
        content_type="text/plain",
    )

    payload = stored_object_payload(stored)

    assert payload == {
        "key": "uploads/file.txt",
        "url": "/cloud-files/uploads/file.txt",
        "size": 10,
        "content_type": "text/plain",
        "provider": "local",
    }