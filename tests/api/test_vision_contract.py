from __future__ import annotations

from tests.helpers.api_contract import (
    assert_json_response,
    assert_vision_analyze_contract,
    assert_vision_chat_contract,
)


def test_vision_analyze_contract(api_client, tiny_png_path):
    with tiny_png_path.open("rb") as file_obj:
        response = api_client.post(
            "/vision/analyze",
            files={"file": ("tiny.png", file_obj, "image/png")},
            data={
                "user_id": "vision-user",
                "prompt": "请分析这张图",
            },
        )

    data = assert_json_response(response)
    assert_vision_analyze_contract(data)

    result = data["result"]
    assert isinstance(result["confidence_report"]["level"], str)
    assert isinstance(result["low_confidence_policy"]["active"], bool)
    assert "confidence_report" in result
    assert "low_confidence_policy" in result
    assert result["metadata"]["vision_graph_status"] == "done"
    assert "vision_graph_latency_ms" in result["metadata"]


def test_vision_chat_contract(api_client, tiny_png_path):
    with tiny_png_path.open("rb") as file_obj:
        response = api_client.post(
            "/vision/chat",
            files={"file": ("tiny.png", file_obj, "image/png")},
            data={
                "user_id": "vision-user",
                "username": "VisionSmoke",
                "prompt": "请看图回复",
            },
        )

    data = assert_json_response(response)
    assert_vision_chat_contract(data)

    vision = data["vision"]
    assert vision["metadata"]["vision_graph"] == "analyzed"
    assert vision["metadata"]["vision_graph_status"] == "done"
    assert "vision_graph_latency_ms" in vision["metadata"]
    assert "vision_low_confidence_active" in vision["metadata"]
    assert "vision_confirmed_character_count" in vision["metadata"]
    assert "vision_candidate_character_count" in vision["metadata"]
    assert vision["result"]["metadata"]["vision_graph_status"] == "done"
    assert "vision_graph_latency_ms" in vision["result"]["metadata"]
