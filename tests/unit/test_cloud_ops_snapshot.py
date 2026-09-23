from cloud.ops_snapshot import (
    admin_token_state,
    build_config_snapshot,
    sanitize_config_value,
)


def test_admin_token_state_detects_missing_token(monkeypatch):
    monkeypatch.delenv("CLOUD_ADMIN_TOKEN", raising=False)

    state = admin_token_state()

    assert state["configured"] is False
    assert state["strong"] is False
    assert "missing" in state["weak_reasons"]


def test_admin_token_state_detects_placeholder_token():
    state = admin_token_state("change-this-admin-token")

    assert state["configured"] is True
    assert state["strong"] is False
    assert "placeholder_like" in state["weak_reasons"]


def test_admin_token_state_accepts_strong_token():
    state = admin_token_state("unit-admin-token-strong-123456")

    assert state["configured"] is True
    assert state["strong"] is True
    assert state["weak_reasons"] == []


def test_sanitize_config_value_redacts_sensitive_keys():
    result = sanitize_config_value(
        "root",
        {
            "safe": "hello",
            "api_key": "secret-key",
            "nested": {
                "password": "secret-password",
                "token": "secret-token",
            },
        },
    )

    assert result["safe"] == "hello"
    assert result["api_key"]["configured"] is True
    assert result["api_key"]["redacted"] == "[redacted]"
    assert result["nested"]["password"]["configured"] is True
    assert result["nested"]["token"]["redacted"] == "[redacted]"


def test_config_snapshot_does_not_expose_secret_values(monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-admin-token-strong-123456")
    monkeypatch.setenv("GPU_API_TOKEN", "gpu-secret-token")

    snapshot = build_config_snapshot()
    text = str(snapshot)

    assert snapshot["ok"] is True
    assert "risk_summary" in snapshot
    assert "security" in snapshot
    assert "storage" in snapshot
    assert "gpu" in snapshot

    assert "gpu-secret-token" not in text
    assert "unit-admin-token-strong-123456" not in text
    assert snapshot["security"]["admin_token"]["configured"] is True
    assert snapshot["security"]["admin_token"]["strong"] is True
    assert snapshot["gpu"]["gpu_api_token"]["redacted"] == "[redacted]"