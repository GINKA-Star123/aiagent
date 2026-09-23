from __future__ import annotations

from aiagent.live2d.payload_contract import normalize_live2d_payload


def test_unknown_emotion_warns_but_keeps_value():
    payload = normalize_live2d_payload({"character": {"emotion": "暴躁"}})

    assert payload["character"]["emotion"] == "暴躁"
    codes = {item["code"] for item in payload["warnings"]}
    assert "unknown_emotion" in codes


def test_known_emotion_has_no_warning():
    payload = normalize_live2d_payload({"character": {"emotion": "happy"}})

    assert payload["character"]["emotion"] == "happy"
    assert payload["warnings"] == []


def test_unknown_expression_and_motion_are_preserved_without_warning():
    payload = normalize_live2d_payload(
        {"character": {"expression": "smile", "motion": "wave"}}
    )

    assert payload["character"]["expression"] == "smile"
    assert payload["character"]["motion"] == "wave"
    assert payload["warnings"] == []


def test_path_traversal_in_asset_fields_is_blocked():
    payload = normalize_live2d_payload(
        {
            "character": {"model3_json": "../../secret/yzl.model3.json"},
            "scene": {"background_file": "/etc/passwd"},
        }
    )

    assert payload["character"]["model3_json"] == ""
    assert payload["scene"]["background_file"] == ""
    codes = {item["code"] for item in payload["warnings"]}
    assert codes == {"unsafe_asset_path"}


def test_unsafe_audio_url_protocol_is_blocked():
    payload = normalize_live2d_payload(
        {"character": {"mouth": {"mode": "audio", "audio_url": "javascript:alert(1)"}}}
    )

    assert payload["character"]["mouth"]["audio_url"] == ""
    assert payload["character"]["mouth"]["mode"] == "audio"
    assert {item["code"] for item in payload["warnings"]} == {"unsafe_audio_url"}


def test_safe_audio_url_is_kept():
    for value in ("/audio/reply.wav", "audio/reply.wav", "https://cdn.example.com/a.wav"):
        payload = normalize_live2d_payload({"character": {"mouth": {"audio_url": value}}})

        assert payload["character"]["mouth"]["audio_url"] == value
        assert payload["warnings"] == []


def test_overlong_field_is_truncated_and_reported():
    payload = normalize_live2d_payload({"character": {"display_name": "阿" * 200}})

    assert len(payload["character"]["display_name"]) == 64
    assert {item["code"] for item in payload["warnings"]} == {"field_truncated"}


def test_invalid_int_falls_back_and_reports():
    payload = normalize_live2d_payload({"character": {"motion_priority": "很高"}})

    assert payload["character"]["motion_priority"] == 1
    assert {item["code"] for item in payload["warnings"]} == {"invalid_int"}


def test_empty_payload_has_no_warnings_and_stable_contract():
    payload = normalize_live2d_payload({})

    assert payload["version"] == "1.0"
    assert payload["warnings"] == []
    assert payload["character"]["mouth"]["mode"] == "idle"
    assert payload["scene"]["background_id"] == "room_default"
