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

    metadata = output.packet.metadata
    for key in [
        "main_graph_status",
        "main_graph_latency_ms",
        "prepare_context_status",
        "state_graph_status",
        "planner_graph_status",
        "rag_graph_status",
        "llm_graph_status",
        "store_memory_status",
        "response_packet_status",
    ]:
        assert key in metadata

    assert metadata["main_graph_status"] == "done"
    assert metadata["prepare_context_status"] == "done"
    assert metadata["vision_graph_status"] == "skipped"
    assert metadata["state_graph_status"] == "done"
    assert metadata["planner_graph_status"] == "done"
    assert metadata["rag_graph_status"] == "done"
    assert metadata["llm_graph_status"] == "done"
    assert metadata["store_memory_status"] == "done"
    assert metadata["response_packet_status"] == "done"


def test_mock_runtime_capabilities_snapshot_shape():
    reset_runtime()

    runtime = get_runtime()
    snapshot = runtime.get_capability_snapshot()

    assert isinstance(snapshot, dict)
    assert "ok" in snapshot
    assert "status" in snapshot
    assert "summary" in snapshot
    assert "items" in snapshot

def test_mock_runtime_can_handle_vision_chat(tiny_png_path):
    reset_runtime()
    try:
        runtime = get_runtime()

        with tiny_png_path.open("rb") as file_obj:
            output = runtime.handle_vision_chat_upload(
                file_obj=file_obj,
                filename="tiny.png",
                user_prompt="请看一下这张图",
                user_id="smoke-user",
                username="Smoke",
            )

        vision_state = output["vision_state"]
        chat_output = output["chat_output"]

        assert vision_state["vision_result"] is not None
        assert isinstance(vision_state["chat_context"], str)
        assert isinstance(vision_state["memory_hint"], str)
        assert isinstance(vision_state["live2d_suggestion"], dict)
        assert "vision_graph" in vision_state["metadata"]

        vision_result = vision_state["vision_result"]
        assert vision_result.confidence_report is not None
        assert vision_result.low_confidence_policy is not None
        assert "vision_low_confidence_active" in vision_result.metadata
        assert vision_result.metadata["vision_graph_status"] == "done"
        assert "vision_graph_latency_ms" in vision_result.metadata

        assert chat_output.packet.reply_text
        assert chat_output.packet.base_reply_text
        assert isinstance(chat_output.packet.live2d, dict)
        assert isinstance(chat_output.packet.metadata, dict)
        assert chat_output.packet.metadata["vision_graph_status"] == "done"
        assert "vision_graph_latency_ms" in chat_output.packet.metadata
    finally:
        reset_runtime()
