from __future__ import annotations

from typing import Any


def assert_json_response(response, expected_status: int = 200) -> dict[str, Any]:
    assert response.status_code == expected_status
    data = response.json()
    assert isinstance(data, dict)
    return data


def assert_ok_response(data: dict[str, Any]) -> None:
    assert data.get("ok") is True
    assert isinstance(data.get("request_id", ""), str)


def assert_error_response(
    data: dict[str, Any],
    *,
    stage: str | None = None,
) -> None:
    assert data.get("ok") is False
    assert isinstance(data.get("stage"), str)
    assert data.get("stage")
    assert isinstance(data.get("error"), str)
    assert data.get("error")
    assert isinstance(data.get("request_id", ""), str)

    if stage is not None:
        assert data["stage"] == stage


def assert_chat_response_contract(data: dict[str, Any]) -> None:
    assert_ok_response(data)

    required_fields = [
        "reply",
        "base_reply_text",
        "emotion",
        "motion",
        "expression",
        "audio_path",
        "audio_url",
        "audio_segments",
        "audio_segment_urls",
        "audio_segment_texts",
        "live2d_command_path",
        "live2d",
        "metadata",
    ]

    for field in required_fields:
        assert field in data, f"missing chat response field: {field}"

    assert isinstance(data["reply"], str)
    assert isinstance(data["metadata"], dict)
    assert isinstance(data["audio_segments"], list)
    assert isinstance(data["audio_segment_urls"], list)
    assert isinstance(data["audio_segment_texts"], list)


def assert_live2d_payload_contract(payload: dict[str, Any]) -> None:
    assert isinstance(payload, dict)

    assert payload.get("version") == "1.0"

    character = payload.get("character")
    scene = payload.get("scene")
    metadata = payload.get("metadata")

    assert isinstance(character, dict)
    assert isinstance(scene, dict)
    assert isinstance(metadata, dict)

    required_character_fields = [
        "character_id",
        "model_id",
        "emotion",
        "expression",
        "expression_file",
        "motion",
        "motion_group",
        "motion_file",
        "motion_priority",
        "mouth",
        "eye",
        "metadata",
    ]

    for field in required_character_fields:
        assert field in character, f"missing live2d character field: {field}"

    assert isinstance(character["mouth"], dict)
    assert isinstance(character["eye"], dict)
    assert isinstance(character["metadata"], dict)

    assert "mode" in character["mouth"]
    assert "audio_url" in character["mouth"]
    assert "blink" in character["eye"]
    assert "look_at" in character["eye"]

    required_scene_fields = [
        "background_id",
        "background_file",
        "lighting",
        "effect",
        "metadata",
    ]

    for field in required_scene_fields:
        assert field in scene, f"missing live2d scene field: {field}"

    assert isinstance(scene["metadata"], dict)