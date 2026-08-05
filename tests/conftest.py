from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_TEST_ROOT = Path(__file__).resolve().parents[1]
_TEST_TMP_ROOT = _TEST_ROOT / "_tmp" / "test-temp"


def _configure_test_temp_dir() -> None:
    _TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    temp_root = str(_TEST_TMP_ROOT)
    os.environ["TMP"] = temp_root
    os.environ["TEMP"] = temp_root
    os.environ["TMPDIR"] = temp_root
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = str(_TEST_TMP_ROOT / "torchinductor")
    tempfile.tempdir = temp_root


def _force_mock_env() -> None:
    mock_env = {
        "APP_ENV": "test",
        "LOG_LEVEL": "WARNING",
        "LLM_PROVIDER": "mock",
        "LLM_MODEL": "mock",
        "ENABLE_MOCK_LLM": "true",
        "STATE_PROVIDER": "mock",
        "STATE_MODEL": "mock",
        "ENABLE_MOCK_STATE": "true",
        "PLANNER_PROVIDER": "mock",
        "PLANNER_MODEL": "mock",
        "ENABLE_MOCK_PLANNER": "true",
        "VISION_PROVIDER": "mock",
        "VISION_MODEL": "",
        "VISION_CHARACTER_EMBEDDING_LOCAL_FILES_ONLY": "true",
        "TTS_PROVIDER": "mock",
        "ENABLE_MOCK_TTS": "true",
        "ENABLE_LOCAL_AUDIO_PLAYBACK": "false",
        "ASR_PROVIDER": "mock",
        "ENABLE_MOCK_ASR": "true",
        "LIVE2D_PROVIDER": "mock",
        "ENABLE_LIVE2D_RUNTIME": "false",
        "CLOUD_MODE": "false",
        "RATE_LIMIT_ENABLED": "false",
        "INFLIGHT_LIMIT_ENABLED": "false",
        "REDIS_URL": "",
        "MEMORY_ENABLE_GRAPH": "false",
        "MEMORY_RESET_VECTOR_STORE": "false",
        "RAG_EMBEDDING_PROVIDER": "huggingface",
        "RAG_EMBEDDING_LOCAL_FILES_ONLY": "true",
        "RAG_EMBEDDING_MODEL_PATH": "",
        "MEMORY_LONG_TERM_DEFAULT_ENABLED": "true",
        "MEMORY_PREFERENCES_PATH": str(_TEST_TMP_ROOT / "memory_preferences.json"),
    }

    for key, value in mock_env.items():
        os.environ[key] = value


def _safe_tmp_name(node_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", node_name).strip("_") or "test"


_configure_test_temp_dir()
_force_mock_env()


@pytest.fixture()
def tmp_path(request: pytest.FixtureRequest) -> Path:
    base = _TEST_TMP_ROOT / "tmp_path"
    base.mkdir(parents=True, exist_ok=True)

    path = base / f"{_safe_tmp_name(request.node.name)}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def api_client():
    from apps.api.http_server import app
    from apps.core.runtime_registry import reset_runtime

    reset_runtime()

    with TestClient(app) as client:
        yield client

    reset_runtime()


@pytest.fixture()
def test_user() -> dict[str, str]:
    return {
        "user_id": "test-user",
        "username": "测试用户",
    }


@pytest.fixture()
def tiny_png_path(tmp_path: Path) -> Path:
    path = tmp_path / "tiny.png"

    # 1x1 透明 PNG
    path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A"
            "0000000D49484452000000010000000108060000001F15C489"
            "0000000D49444154789C6360606060000000050001A5F64540"
            "0000000049454E44AE426082"
        )
    )

    return path
