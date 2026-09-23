from __future__ import annotations

from aiagent.common.log_safety import (
    REDACTED,
    content_summary,
    safe_json_dumps,
    sanitize_log_value,
    sanitize_text,
)


def test_sanitize_text_redacts_authorization():
    text = sanitize_text(
        "Authorization: Bearer very-secret-token"
    )

    assert "very-secret-token" not in text
    assert REDACTED in text


def test_sanitize_text_redacts_key_value_secret():
    text = sanitize_text(
        "OPENAI_API_KEY=sk-unit-secret password=123456"
    )

    assert "sk-unit-secret" not in text
    assert "123456" not in text
    assert text.count(REDACTED) >= 2


def test_sanitize_text_redacts_json_secret():
    text = sanitize_text(
        '{"user_id":"u1","token":"secret-token"}'
    )

    assert "secret-token" not in text
    assert REDACTED in text


def test_sanitize_text_redacts_data_url():
    text = sanitize_text(
        "image=data:image/png;base64,"
        + ("A" * 500)
    )

    assert "A" * 100 not in text
    assert "base64" in text
    assert REDACTED in text


def test_sanitize_log_value_recursively_redacts_secrets():
    result = sanitize_log_value(
        {
            "user_id": "u1",
            "api_key": "api-secret",
            "nested": {
                "password": "password-secret",
                "safe": "visible",
            },
        }
    )

    assert result["user_id"] == "u1"
    assert result["api_key"] == REDACTED
    assert result["nested"]["password"] == REDACTED
    assert result["nested"]["safe"] == "visible"


def test_sanitize_log_value_redacts_bytes():
    result = sanitize_log_value(
        {
            "audio_data": b"audio-secret",
            "payload": b"raw-data",
        }
    )

    assert result["audio_data"] == "[binary-content-redacted]"
    assert "audio-secret" not in str(result)
    assert "raw-data" not in str(result)


def test_safe_json_dumps_does_not_leak_secret():
    text = safe_json_dumps(
        {
            "authorization": "Bearer secret",
            "safe": "value",
        }
    )

    assert "Bearer secret" not in text
    assert '"safe":"value"' in text


def test_content_summary_returns_hash_and_length():
    summary = content_summary("你好，测试 Prompt")

    assert summary["empty"] is False
    assert summary["length"] == len("你好，测试 Prompt")
    assert isinstance(summary["sha256"], str)
    assert len(summary["sha256"]) == 16
    assert "preview" not in summary


def test_content_summary_preview_is_opt_in():
    summary = content_summary(
        "hello token=secret-value",
        include_preview=True,
    )

    assert "preview" in summary
    assert "secret-value" not in summary["preview"]


# --- 回归防护：下划线前缀的环境变量风格（曾因正则使用 \b 而整体漏脱敏） ---


def test_sanitize_text_redacts_underscore_prefixed_env_secrets():
    text = sanitize_text(
        "OPENAI_API_KEY=sk-unit-secret "
        "DB_PASSWORD=db-unit-secret "
        "JWT_SECRET=jwt-unit-secret "
        "MY_TOKEN=my-unit-secret"
    )

    assert "sk-unit-secret" not in text
    assert "db-unit-secret" not in text
    assert "jwt-unit-secret" not in text
    assert "my-unit-secret" not in text
    assert text.count(REDACTED) == 4


def test_sanitize_text_redacts_underscore_prefixed_authorization():
    text = sanitize_text("X_AUTHORIZATION: Bearer auth-unit-secret")

    assert "auth-unit-secret" not in text
    assert REDACTED in text


def test_sanitize_text_redacts_json_multiple_secrets():
    text = sanitize_text(
        '{"api_key":"key-unit-secret",'
        '"password":"pwd-unit-secret",'
        '"token":"token-unit-secret"}'
    )

    assert "key-unit-secret" not in text
    assert "pwd-unit-secret" not in text
    assert "token-unit-secret" not in text
    assert text.count(REDACTED) == 3


def test_sanitize_text_redacts_json_with_spaces():
    text = sanitize_text('{"token" : "spaced-unit-secret"}')

    assert "spaced-unit-secret" not in text
    assert REDACTED in text


def test_sanitize_text_keeps_non_secret_lookalikes():
    """反例护栏：边界放宽后也不能误伤这些非敏感字段。"""

    text = sanitize_text("tokenizer=abc token_count=3")

    assert "tokenizer=abc" in text
    assert "token_count=3" in text
    assert REDACTED not in text
