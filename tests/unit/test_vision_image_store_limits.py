from __future__ import annotations

import io

import pytest
from PIL import Image

from aiagent.vision.image_store import ImageStore, sniff_image_format


def _png_bytes(width: int = 32, height: int = 32) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 160, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_rejects_unsupported_extension(tmp_path):
    store = ImageStore(upload_dir=tmp_path, max_bytes=5_000_000)
    with pytest.raises(ValueError):
        store.save_upload(io.BytesIO(_png_bytes()), "note.txt")


def test_upload_rejects_empty_file(tmp_path):
    store = ImageStore(upload_dir=tmp_path, max_bytes=5_000_000)
    with pytest.raises(ValueError):
        store.save_upload(io.BytesIO(b""), "empty.png")


def test_upload_rejects_non_image_content_with_image_extension(tmp_path):
    store = ImageStore(upload_dir=tmp_path, max_bytes=5_000_000)
    with pytest.raises(ValueError):
        store.save_upload(io.BytesIO(b"PK\x03\x04 this is a zip"), "fake.png")


def test_upload_rejects_oversized_stream(tmp_path):
    store = ImageStore(upload_dir=tmp_path, max_bytes=128)
    with pytest.raises(ValueError):
        store.save_upload(io.BytesIO(_png_bytes(256, 256)), "big.png")


def test_upload_rejects_excessive_pixels(tmp_path):
    store = ImageStore(upload_dir=tmp_path, max_bytes=20_000_000, max_pixels=100)
    with pytest.raises(ValueError):
        store.save_upload(io.BytesIO(_png_bytes(64, 64)), "bomb.png")


def test_local_copy_rejects_oversized_file_before_reading(tmp_path):
    source = tmp_path / "huge.png"
    source.write_bytes(_png_bytes(64, 64))
    store = ImageStore(upload_dir=tmp_path / "uploads", max_bytes=32)

    with pytest.raises(ValueError):
        store.save_local_copy(source)


def test_valid_upload_is_stored_with_metadata(tmp_path):
    store = ImageStore(upload_dir=tmp_path, max_bytes=5_000_000)
    stored = store.save_upload(io.BytesIO(_png_bytes(48, 24)), "ok.png")

    assert stored.width == 48
    assert stored.height == 24
    assert stored.format == "PNG"
    assert stored.path.exists()
    assert len(stored.sha256) == 64
    assert sniff_image_format(stored.path) == "PNG"