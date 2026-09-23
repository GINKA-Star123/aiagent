from __future__ import annotations

from cloud.readiness import (
    ReadinessCheck,
    ReadinessSnapshot,
    ReadinessStatus,
    redact_snapshot,
)


def _snapshot() -> ReadinessSnapshot:
    return ReadinessSnapshot(
        ok=True,
        status=ReadinessStatus.DEGRADED,
        checks={"redis": True, "runtime_import": False},
        summary={"total": 2, "required_failed": 0, "optional_failed": 1},
        items=[
            ReadinessCheck(
                name="redis",
                ok=True,
                required=True,
                summary="Redis is available.",
                action="检查 REDIS_URL。",
                details={"ok": True, "enabled": True, "url": "redis://internal-host:6379/0"},
            ),
            ReadinessCheck(
                name="cloud_admin_token",
                ok=True,
                required=True,
                summary="Cloud admin token is configured.",
                details={"configured": True, "length": 64},
            ),
        ],
        cloud_mode=True,
        purpose="ops",
        details={"risk_summary": {"critical": 0}, "gpu": {"llm": {"base_url": "http://gpu:8000"}}},
    )


def test_redact_snapshot_removes_all_internal_details():
    redacted = redact_snapshot(_snapshot())

    assert redacted.details == {}
    assert all(item.details == {} for item in redacted.items)
    assert all(item.action == "" for item in redacted.items)

    dumped = redacted.model_dump(mode="json")
    text = str(dumped)
    for secret in ["redis://internal-host", "gpu:8000", "risk_summary", "length"]:
        assert secret not in text


def test_redact_snapshot_keeps_public_signals():
    redacted = redact_snapshot(_snapshot())

    assert redacted.status == ReadinessStatus.DEGRADED
    assert redacted.checks == {"redis": True, "runtime_import": False}
    assert redacted.summary["optional_failed"] == 1
    assert redacted.cloud_mode is True
    assert {item.name for item in redacted.items} == {"redis", "cloud_admin_token"}
    assert redacted.items[0].summary == "Redis is available."
