from __future__ import annotations

from apps.core.runtime_registry import get_runtime
from tests.helpers.api_contract import (
    assert_chat_response_contract,
    assert_error_response,
    assert_json_response,
    assert_live2d_payload_contract,
    assert_voice_realtime_metadata_contract,
    assert_voice_realtime_response_contract,
)


def _start_call(api_client, test_user) -> str:
    response = api_client.post(
        "/voice/realtime/start",
        json={
            "user_id": test_user["user_id"],
            "username": test_user["username"],
        },
    )
    data = assert_json_response(response)
    assert_voice_realtime_response_contract(data)

    call_id = data["call_id"]
    assert call_id
    assert data["status"] == "active"
    assert data["phase"] == "idle"
    assert data["turn_count"] == 0
    assert data["turn_id"] == ""

    assert_voice_realtime_metadata_contract(
        data["metadata"],
        required_stages=["call_start"],
    )
    assert data["metadata"]["voice_call_start_status"] == "done"

    return call_id


def test_voice_realtime_start_state_end_contract(api_client, test_user):
    call_id = _start_call(api_client, test_user)

    state_response = api_client.get(f"/voice/realtime/state/{call_id}")
    state_data = assert_json_response(state_response)

    assert_voice_realtime_response_contract(state_data)
    assert state_data["call_id"] == call_id
    assert state_data["status"] == "active"
    assert state_data["phase"] == "idle"
    assert state_data["turn_count"] == 0
    assert state_data["turn_id"] == ""

    end_response = api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": call_id,
        },
    )
    end_data = assert_json_response(end_response)

    assert_voice_realtime_response_contract(end_data)
    assert end_data["call_id"] == call_id
    assert end_data["status"] == "ended"
    assert end_data["phase"] == "completed"
    assert end_data["call"]["status"] == "ended"
    assert end_data["call"]["phase"] == "completed"
    assert end_data["call"]["ended_at"]

    assert_voice_realtime_metadata_contract(
        end_data["metadata"],
        required_stages=["call_end"],
    )
    assert end_data["metadata"]["voice_call_end_status"] == "done"


def test_voice_realtime_turn_success_contract(api_client, test_user, tmp_path):
    call_id = _start_call(api_client, test_user)

    audio_path = tmp_path / "mock-turn.m4a"
    audio_path.write_bytes(b"mock audio bytes")

    with audio_path.open("rb") as file_obj:
        response = api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": call_id,
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={
                "file": ("mock-turn.m4a", file_obj, "audio/mp4"),
            },
        )

    data = assert_json_response(response)

    assert_voice_realtime_response_contract(data)
    assert_chat_response_contract(data)
    assert_live2d_payload_contract(data["live2d"])

    assert data["call_id"] == call_id
    assert data["turn_count"] == 1
    assert data["turn_id"].endswith(":1")
    assert data["transcript"]
    assert data["reply"]
    assert data["metadata"]["voice_turn_empty"] is False
    assert data["metadata"]["voice_chat_status"] == "done"
    assert data["metadata"]["voice_turn_status"] == "done"
    assert data["phase"] in {"speaking", "completed"}

    assert_voice_realtime_metadata_contract(
        data["metadata"],
        required_stages=["upload", "asr", "chat", "tts", "turn"],
    )


def test_voice_realtime_empty_turn_contract(
    api_client,
    test_user,
    tmp_path,
    monkeypatch,
):
    call_id = _start_call(api_client, test_user)

    runtime = get_runtime()
    monkeypatch.setattr(runtime, "transcribe_audio_file", lambda _audio_path: "   ")

    audio_path = tmp_path / "empty-turn.m4a"
    audio_path.write_bytes(b"mock audio bytes")

    with audio_path.open("rb") as file_obj:
        response = api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": call_id,
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={
                "file": ("empty-turn.m4a", file_obj, "audio/mp4"),
            },
        )

    data = assert_json_response(response)

    assert_voice_realtime_response_contract(data)
    assert_chat_response_contract(data)
    assert_live2d_payload_contract(data["live2d"])

    assert data["call_id"] == call_id
    assert data["turn_count"] == 1
    assert data["phase"] == "empty_turn"
    assert data["transcript"] == ""
    assert data["reply"] == ""
    assert data["output_id"] == ""

    metadata = data["metadata"]
    assert_voice_realtime_metadata_contract(
        metadata,
        required_stages=["upload", "asr", "chat", "tts", "turn"],
    )
    assert metadata["voice_asr_empty"] is True
    assert metadata["voice_turn_empty"] is True
    assert metadata["voice_chat_status"] == "skipped"
    assert metadata["voice_chat_skip_reason"] == "empty_transcript"
    assert metadata["voice_tts_status"] == "skipped"


def test_voice_realtime_interrupt_active_call_contract(api_client, test_user):
    call_id = _start_call(api_client, test_user)

    response = api_client.post(
        "/voice/realtime/interrupt",
        json={
            "call_id": call_id,
            "reason": "unit_interrupt",
        },
    )

    data = assert_json_response(response)

    assert_voice_realtime_response_contract(data)
    assert data["call_id"] == call_id
    assert data["status"] == "active"
    assert data["phase"] == "interrupted"
    assert data["call"]["interrupt_count"] == 1
    assert data["call"]["last_interrupt_reason"] == "unit_interrupt"

    assert "result" in data
    assert data["result"]["status"] == "interrupted"
    assert data["result"]["reason"] == "unit_interrupt"

    assert_voice_realtime_metadata_contract(
        data["metadata"],
        required_stages=["interrupt"],
    )
    assert data["metadata"]["voice_interrupt_reason"] == "unit_interrupt"
    assert data["metadata"]["voice_interrupt_status"] == "done"


def test_voice_realtime_state_missing_call_contract(api_client):
    response = api_client.get("/voice/realtime/state/missing-call-id")
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="voice_realtime_state")


def test_voice_realtime_turn_missing_call_contract(api_client, test_user, tmp_path):
    audio_path = tmp_path / "empty.m4a"
    audio_path.write_bytes(b"")

    with audio_path.open("rb") as file_obj:
        response = api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": "missing-call-id",
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={
                "file": ("empty.m4a", file_obj, "audio/mp4"),
            },
        )

    data = assert_json_response(response, expected_status=404)
    assert_error_response(data, stage="voice_realtime_turn")


def test_voice_realtime_interrupt_missing_call_contract(api_client):
    response = api_client.post(
        "/voice/realtime/interrupt",
        json={
            "call_id": "missing-call-id",
            "reason": "unit_interrupt",
        },
    )

    data = assert_json_response(response, expected_status=404)
    assert_error_response(data, stage="voice_realtime_interrupt")