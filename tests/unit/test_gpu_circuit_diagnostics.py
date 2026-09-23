from __future__ import annotations

from aiagent.diagnostics.runtime_diagnostics import RuntimeDiagnostics
from cloud import gpu_client as gpu_client_module


class _FakeClient:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def circuit_snapshot_all(self):
        return self._snapshot


def _install(monkeypatch, snapshot):
    monkeypatch.setattr(gpu_client_module, "gpu_client", _FakeClient(snapshot))


def test_gpu_circuit_check_is_ok_when_all_closed(monkeypatch):
    _install(
        monkeypatch,
        {
            "llm": {"name": "llm", "state": "closed", "failure_count": 0, "last_error": "", "allow_request": True},
            "tts": {"name": "tts", "state": "closed", "failure_count": 0, "last_error": "", "allow_request": True},
        },
    )

    check = RuntimeDiagnostics()._check_gpu_circuit()

    assert check.name == "gpu_circuit"
    assert check.status == "ok"
    assert check.details["open_circuits"] == []


def test_gpu_circuit_check_degrades_when_open(monkeypatch):
    _install(
        monkeypatch,
        {
            "llm": {
                "name": "llm",
                "state": "open",
                "failure_count": 3,
                "last_error": "connect timeout",
                "allow_request": False,
            },
            "tts": {"name": "tts", "state": "closed", "failure_count": 0, "last_error": "", "allow_request": True},
        },
    )

    check = RuntimeDiagnostics()._check_gpu_circuit()

    assert check.status == "degraded"
    assert check.details["open_circuits"] == ["llm"]
    assert check.details["circuits"]["llm"]["last_error"] == "connect timeout"
    assert check.action


def test_failure_policy_check_lists_redis_dependencies():
    check = RuntimeDiagnostics()._check_cloud_failure_policy()

    assert check.name == "cloud_failure_policy"
    assert check.status == "ok"
    modes = {item["dependency"]: item["failure_mode"] for item in check.details["policy"]}
    assert modes["task_queue"] == "fail_closed"
    assert modes["rate_limit"] == "fail_open"
