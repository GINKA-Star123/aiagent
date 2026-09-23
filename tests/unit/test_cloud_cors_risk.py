from __future__ import annotations

from cloud.config import cloud_settings
from cloud.ops_snapshot import build_config_snapshot
from config.settings import settings


def _risk_keys(snapshot: dict) -> list[str]:
    return [item["key"] for item in snapshot["risk_summary"]["items"]]


def test_loopback_cors_with_credentials_in_cloud_mode_is_flagged(monkeypatch):
    monkeypatch.setattr(settings, "api_cors_origins", "http://localhost:3000,http://127.0.0.1:3000")
    monkeypatch.setattr(settings, "api_cors_allow_credentials", True)
    monkeypatch.setattr(cloud_settings, "cloud_mode", True)

    snapshot = build_config_snapshot()

    assert "cors_loopback_origins_in_cloud_mode" in _risk_keys(snapshot)
    assert snapshot["security"]["cors"]["loopback_origins"] == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_wildcard_cors_with_credentials_is_critical(monkeypatch):
    monkeypatch.setattr(settings, "api_cors_origins", "*")
    monkeypatch.setattr(settings, "api_cors_allow_credentials", True)
    monkeypatch.setattr(cloud_settings, "cloud_mode", False)

    snapshot = build_config_snapshot()

    assert "cors_wildcard_with_credentials" in _risk_keys(snapshot)
    assert snapshot["security"]["cors"]["wildcard"] is True


def test_production_cors_without_loopback_is_not_flagged(monkeypatch):
    monkeypatch.setattr(settings, "api_cors_origins", "https://app.example.com")
    monkeypatch.setattr(settings, "api_cors_allow_credentials", True)
    monkeypatch.setattr(cloud_settings, "cloud_mode", True)

    snapshot = build_config_snapshot()
    keys = _risk_keys(snapshot)

    assert "cors_loopback_origins_in_cloud_mode" not in keys
    assert "cors_wildcard_with_credentials" not in keys
