from __future__ import annotations

from apps.core.runtime_registry import get_runtime, reset_runtime


def test_mock_runtime_can_build():
    reset_runtime()

    runtime = get_runtime()

    assert runtime is not None
    assert runtime.dispatcher is not None
    assert runtime.agent_core is not None
    assert runtime.llm_service is not None


def test_mock_runtime_can_handle_text_chat():
    reset_runtime()

    runtime = get_runtime()
    output = runtime.handle_chat_full(
        text="你好",
        user_id="smoke-user",
        username="Smoke",
    )

    assert output.output_id
    assert output.packet.reply_text
    assert output.packet.metadata is not None


def test_mock_runtime_capabilities_snapshot_shape():
    reset_runtime()

    runtime = get_runtime()
    snapshot = runtime.get_capability_snapshot()

    assert isinstance(snapshot, dict)
    assert "ok" in snapshot
    assert "status" in snapshot
    assert "summary" in snapshot
    assert "items" in snapshot