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

def assert_vision_result_contract(result: dict[str, Any]) -> None:
    assert isinstance(result, dict)

    required_fields = [
        "image_id",
        "image_path",
        "image_url",
        "width",
        "height",
        "format",
        "image_type",
        "user_intent",
        "summary",
        "objects",
        "scene",
        "daily_scene",
        "ocr_text",
        "mood",
        "character_candidates",
        "recognized_characters",
        "is_confident",
        "confidence",
        "confidence_report",
        "low_confidence_policy",
        "safety",
        "memory",
        "live2d",
        "channels",
        "schema_violations",
        "memory_decision",
        "metadata",
    ]
    for field in required_fields:
        assert field in result, f"missing vision result field: {field}"

    assert isinstance(result["channels"], dict)
    for channel in ["ocr", "scene", "character"]:
        assert channel in result["channels"], f"missing vision channel: {channel}"
        assert result["channels"][channel]["status"] in {"ok", "partial", "missing", "skipped"}

    assert isinstance(result["schema_violations"], list)
    assert isinstance(result["memory_decision"], dict)
    assert isinstance(result["memory_decision"]["allow"], bool)
    assert result["memory_decision"]["reason_code"]

    for field in [
        "image_id",
        "image_path",
        "image_url",
        "format",
        "image_type",
        "user_intent",
        "summary",
        "scene",
        "mood",
    ]:
        assert isinstance(result[field], str)

    assert isinstance(result["width"], int)
    assert isinstance(result["height"], int)
    assert isinstance(result["confidence"], (int, float))
    assert isinstance(result["is_confident"], bool)
    assert isinstance(result["objects"], list)
    assert isinstance(result["ocr_text"], list)
    assert isinstance(result["character_candidates"], list)
    assert isinstance(result["recognized_characters"], list)
    assert isinstance(result["daily_scene"], dict)
    assert isinstance(result["confidence_report"], dict)
    assert isinstance(result["low_confidence_policy"], dict)
    assert isinstance(result["safety"], dict)
    assert isinstance(result["memory"], dict)
    assert isinstance(result["live2d"], dict)
    assert isinstance(result["metadata"], dict)

    daily_scene = result["daily_scene"]
    for field in [
        "scene_type",
        "location_hint",
        "activity",
        "food",
        "landmarks",
        "objects",
        "people_count",
        "time_hint",
        "weather_hint",
        "notable_details",
    ]:
        assert field in daily_scene, f"missing daily_scene field: {field}"

    confidence_report = result["confidence_report"]
    for field in [
        "score",
        "level",
        "threshold",
        "source",
        "reason",
        "evidence",
        "character_score",
        "model_score",
        "best_retrieval_score",
        "best_character_id",
        "best_character_name",
        "candidate_count",
    ]:
        assert field in confidence_report, f"missing confidence_report field: {field}"

    assert confidence_report["level"] in {"high", "medium", "low", "uncertain"}
    assert confidence_report["source"] in {
        "character_identity",
        "scene_understanding",
        "unknown_image_type",
    }
    assert isinstance(confidence_report["evidence"], list)

    low_policy = result["low_confidence_policy"]
    for field in [
        "active",
        "reason",
        "use_conservative_wording",
        "avoid_identity_assertion",
        "expose_candidates",
        "defer_memory_hint",
        "suppress_live2d_override",
        "reply_instruction",
    ]:
        assert field in low_policy, f"missing low_confidence_policy field: {field}"

    safety = result["safety"]
    for field in ["has_sensitive_content", "risk_level", "reason"]:
        assert field in safety, f"missing safety field: {field}"

    memory = result["memory"]
    for field in ["should_consider", "reason"]:
        assert field in memory, f"missing memory field: {field}"

    live2d = result["live2d"]
    for field in [
        "suggested_emotion",
        "suggested_expression",
        "suggested_motion",
        "suggested_background",
    ]:
        assert field in live2d, f"missing live2d field: {field}"

    for item in result["character_candidates"] + result["recognized_characters"]:
        assert isinstance(item, dict)
        for field in [
            "character_id",
            "name",
            "confidence",
            "score",
            "evidence",
            "metadata",
        ]:
            assert field in item, f"missing character item field: {field}"

    if "schema_version" in result:
        assert isinstance(result["schema_version"], str)
    if "identity_confirmed" in result:
        assert isinstance(result["identity_confirmed"], bool)


def assert_vision_analyze_contract(data: dict[str, Any]) -> None:
    assert_ok_response(data)
    assert "result" in data
    assert isinstance(data["result"], dict)
    assert_vision_result_contract(data["result"])


def assert_vision_chat_contract(data: dict[str, Any]) -> None:
    assert_ok_response(data)
    assert "vision" in data
    vision = data["vision"]
    assert isinstance(vision, dict)

    for field in ["result", "chat_context", "memory_hint", "live2d_suggestion", "metadata"]:
        assert field in vision, f"missing vision chat field: {field}"

    assert isinstance(vision["chat_context"], str)
    assert isinstance(vision["memory_hint"], str)
    assert isinstance(vision["live2d_suggestion"], dict)
    assert isinstance(vision["metadata"], dict)
    assert_vision_result_contract(vision["result"])

def assert_voice_realtime_call_contract(call: dict[str, Any]) -> None:
    assert isinstance(call, dict)

    required_fields = [
        "call_id",
        "user_id",
        "username",
        "status",
        "phase",
        "started_at",
        "last_seen_at",
        "phase_changed_at",
        "ended_at",
        "turn_count",
        "last_turn_id",
        "last_transcript",
        "last_output_id",
        "last_audio_path",
        "last_audio_url",
        "interrupt_count",
        "last_interrupt_reason",
        "last_error",
        "metadata",
    ]

    for field in required_fields:
        assert field in call, f"missing voice call field: {field}"

    assert isinstance(call["call_id"], str)
    assert call["status"] in {"active", "ended", "error"}
    assert call["phase"] in {
        "idle",
        "listening",
        "uploaded",
        "transcribing",
        "thinking",
        "speaking",
        "empty_turn",
        "interrupted",
        "completed",
        "failed",
    }
    assert isinstance(call["turn_count"], int)
    assert isinstance(call["interrupt_count"], int)
    assert isinstance(call["metadata"], dict)


def assert_voice_realtime_response_contract(data: dict[str, Any]) -> None:
    assert_ok_response(data)

    required_fields = [
        "call_id",
        "status",
        "phase",
        "turn_id",
        "turn_count",
        "last_seen_at",
        "phase_changed_at",
        "metadata",
        "call",
    ]

    for field in required_fields:
        assert field in data, f"missing voice realtime response field: {field}"

    assert isinstance(data["call_id"], str)
    assert data["status"] in {"active", "ended", "error"}
    assert data["phase"] in {
        "idle",
        "listening",
        "uploaded",
        "transcribing",
        "thinking",
        "speaking",
        "empty_turn",
        "interrupted",
        "completed",
        "failed",
    }
    assert isinstance(data["turn_count"], int)
    assert isinstance(data["metadata"], dict)
    assert_voice_realtime_call_contract(data["call"])


def assert_voice_realtime_metadata_contract(
    metadata: dict[str, Any],
    *,
    required_stages: list[str],
) -> None:
    assert isinstance(metadata, dict)
    assert metadata.get("voice_realtime") is True
    assert isinstance(metadata.get("voice_realtime_call_id"), str)
    assert "voice_realtime_phase" in metadata

    for stage in required_stages:
        status_key = f"voice_{stage}_status"
        assert status_key in metadata, f"missing voice metadata field: {status_key}"
        assert metadata[status_key] in {"done", "skipped", "failed"}

