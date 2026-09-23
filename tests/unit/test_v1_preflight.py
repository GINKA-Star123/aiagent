# tests/unit/test_v1_preflight.py
from __future__ import annotations

import importlib.util
import sys                      # ← 新增
from pathlib import Path


def load_preflight_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "v1_preflight.py"

    spec = importlib.util.spec_from_file_location("v1_preflight", path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    # Python 3.12 起，dataclasses 处理"字符串注解"时会查 sys.modules[cls.__module__]。
    # 手工 exec 的模块默认不在 sys.modules 里，必须在 exec_module 之前注册，
    # 否则 @dataclass(frozen=True) 会抛 AttributeError: 'NoneType' object has no attribute '__dict__'。
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_env_file_detects_duplicate_keys(tmp_path):
    preflight = load_preflight_module()

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# comment",
                "LLM_PROVIDER=mock",
                "LLM_PROVIDER=siliconflow",
                "ENABLE_MOCK_LLM=false",
            ]
        ),
        encoding="utf-8",
    )

    parsed = preflight.parse_env_file(env_path)

    assert parsed.values["LLM_PROVIDER"] == "siliconflow"
    assert parsed.duplicates == [("LLM_PROVIDER", 3)]
    assert parsed.malformed == []


def test_docs_key_coverage_reports_missing_key(tmp_path):
    preflight = load_preflight_module()

    env_path = tmp_path / ".env.example"
    doc_path = tmp_path / "config-reference.md"

    env_path.write_text("LLM_PROVIDER=mock\nNEW_CONFIG_KEY=value\n", encoding="utf-8")
    doc_path.write_text("`LLM_PROVIDER` is documented.\n", encoding="utf-8")

    parsed = preflight.parse_env_file(env_path)
    issues = []

    preflight.check_docs_key_coverage([parsed], doc_path, issues)

    assert any(issue.check == "docs_env_coverage" for issue in issues)
    assert any("NEW_CONFIG_KEY" in issue.message for issue in issues)


def test_production_env_rejects_placeholders_and_mock(tmp_path):
    preflight = load_preflight_module()

    env_path = tmp_path / "cloud.tencent.env"
    env_path.write_text(
        "\n".join(
            [
                "CLOUD_MODE=true",
                "RATE_LIMIT_ENABLED=true",
                "INFLIGHT_LIMIT_ENABLED=true",
                "LIMITER_FAIL_OPEN=false",
                "CLOUD_ADMIN_TOKEN=change-this-admin-token",
                "API_PUBLIC_BASE_URL=https://your-domain.example.com",
                "POSTGRES_PASSWORD=change-me-postgres-password",
                "LLM_PROVIDER=mock",
                "ENABLE_MOCK_LLM=true",
                "STATE_PROVIDER=mock",
                "ENABLE_MOCK_STATE=true",
                "PLANNER_PROVIDER=mock",
                "ENABLE_MOCK_PLANNER=true",
                "TTS_PROVIDER=mock",
                "ENABLE_MOCK_TTS=true",
                "ASR_PROVIDER=mock",
                "ENABLE_MOCK_ASR=true",
                "VISION_PROVIDER=mock",
                "STORAGE_PROVIDER=cos",
                "S3_ENDPOINT_URL=https://cos.ap-guangzhou.myqcloud.com",
                "S3_REGION=ap-guangzhou",
                "S3_BUCKET=your-bucket-name",
                "S3_ACCESS_KEY_ID=your-secret-id",
                "S3_SECRET_ACCESS_KEY=your-secret-key",
                "S3_PUBLIC_BASE_URL=https://your-bucket.example.com",
                "MEMORY_RESET_VECTOR_STORE=true",
            ]
        ),
        encoding="utf-8",
    )

    parsed = preflight.parse_env_file(env_path)
    issues = []

    preflight.check_production_env(parsed, issues, allow_prod_mock=False)

    error_messages = "\n".join(issue.message for issue in issues if issue.severity == "error")

    assert "CLOUD_ADMIN_TOKEN" in error_messages
    assert "LLM_PROVIDER=mock" in error_messages
    assert "MEMORY_RESET_VECTOR_STORE=true" in error_messages


def test_production_env_accepts_minimal_real_provider_combo(tmp_path):
    preflight = load_preflight_module()

    env_path = tmp_path / "cloud.tencent.env"
    env_path.write_text(
        "\n".join(
            [
                "CLOUD_MODE=true",
                "RATE_LIMIT_ENABLED=true",
                "INFLIGHT_LIMIT_ENABLED=true",
                "LIMITER_FAIL_OPEN=false",
                "CLOUD_ADMIN_TOKEN=real-admin-token",
                "API_PUBLIC_BASE_URL=https://aiagent.example.net",
                "API_CORS_ORIGINS=https://aiagent.example.net",
                "POSTGRES_PASSWORD=real-postgres-password",
                "LLM_PROVIDER=siliconflow",
                "ENABLE_MOCK_LLM=false",
                "STATE_PROVIDER=siliconflow",
                "ENABLE_MOCK_STATE=false",
                "PLANNER_PROVIDER=siliconflow",
                "ENABLE_MOCK_PLANNER=false",
                "SILICONFLOW_API=real-siliconflow-key",
                "SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1",
                "OPENAI_API_KEY=real-openai-compatible-key",
                "OPENAI_BASE_URL=https://api.siliconflow.cn/v1",
                "TTS_PROVIDER=gpt_sovits",
                "ENABLE_MOCK_TTS=false",
                "GPT_SOVITS_BASE_URL=http://tts.internal",
                "ASR_PROVIDER=api",
                "ENABLE_MOCK_ASR=false",
                "ASR_API_BASE_URL=https://asr.example.net",
                "ASR_API_KEY=real-asr-key",
                "RAG_EMBEDDING_PROVIDER=siliconflow",
                "RAG_EMBEDDING_API_KEY_ENV=SILICONFLOW_API",
                "RAG_EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1",
                "RAG_EMBEDDING_DIMENSIONS=1024",
                "VISION_PROVIDER=siliconflow",
                "VISION_MODEL=Qwen/Qwen2.5-VL-7B-Instruct",
                "VISION_BASE_URL=https://api.siliconflow.cn/v1",
                "VISION_API_KEY_ENV=SILICONFLOW_API",
                "STORAGE_PROVIDER=cos",
                "S3_ENDPOINT_URL=https://cos.ap-guangzhou.myqcloud.com",
                "S3_REGION=ap-guangzhou",
                "S3_BUCKET=real-bucket",
                "S3_ACCESS_KEY_ID=real-secret-id",
                "S3_SECRET_ACCESS_KEY=real-secret-key",
                "S3_PUBLIC_BASE_URL=https://real-bucket.cos.ap-guangzhou.myqcloud.com",
                "MEMORY_LLM_PROVIDER=openai",
                "MEMORY_LLM_API_KEY_ENV=OPENAI_API_KEY",
                "MEMORY_EMBEDDER_PROVIDER=openai",
                "MEMORY_EMBEDDER_API_KEY_ENV=OPENAI_API_KEY",
                "MEMORY_ENABLE_GRAPH=true",
                "NEO4J_PASSWORD=real-neo4j-password",
                "MEMORY_RESET_VECTOR_STORE=false",
                "LIVE2D_PROVIDER=mock",
            ]
        ),
        encoding="utf-8",
    )

    parsed = preflight.parse_env_file(env_path)
    issues = []

    preflight.check_production_env(parsed, issues, allow_prod_mock=False)

    errors = [issue for issue in issues if issue.severity == "error"]

    assert errors == []