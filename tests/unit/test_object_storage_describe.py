from __future__ import annotations

import asyncio

import pytest

from cloud.object_storage import (
    LocalObjectStore,
    ObjectStorageValidationError,
    build_object_key,
    normalize_storage_prefix,
)


def test_build_object_key_is_provider_agnostic():
    key = build_object_key("uploads", "头像 final.PNG")

    assert key.startswith("uploads/")
    assert key.lower().endswith(".png")
    assert "\\" not in key
    assert ".." not in key


def test_normalize_storage_prefix_rejects_traversal_and_collapses_slashes():
    with pytest.raises(ObjectStorageValidationError):
        normalize_storage_prefix("../etc")

    assert normalize_storage_prefix("  a//b/  ") == "a/b"


def test_local_store_describe_matches_protocol_keys(tmp_path):
    store = LocalObjectStore(root=str(tmp_path), public_base_url="http://127.0.0.1:8000")
    described = store.describe()

    assert described["provider"] == "local"
    assert described["root"] == str(tmp_path)
    assert described["url_prefix"].endswith("/cloud-files")
    assert described["presigned_supported"] is False

    stored = asyncio.run(store.put_bytes("uploads/a.txt", b"hello", "text/plain"))
    assert stored.key == "uploads/a.txt"
    assert stored.url.startswith("http://127.0.0.1:8000/cloud-files/")
