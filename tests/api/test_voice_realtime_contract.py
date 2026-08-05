from __future__ import annotations

from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
    assert_ok_response,
)


def test_voice_realtime_start_state_end_contract(api_client, test_user):
    start_response = api_client.post(
        "/voice/realtime/start",
        json={
            "user_id": test_user["user_id"],
            "username": test_user["username"],
        },
    )
    start_data = assert_json_response(start_response)
    assert_ok_response(start_data)
    

    call_id = start_data.get("call_id")
    assert isinstance(call_id, str)
    assert call_id
    assert start_data["status"] == "active"
    assert start_data["phase"] == "idle"
    assert "call" in start_data
    assert start_data["call"]["call_id"] == call_id
    assert start_data["call"]["status"] == "active"
    assert start_data["call"]["phase"] == "idle"

    state_response = api_client.get(f"/voice/realtime/state/{call_id}")
    state_data = assert_json_response(state_response)
    assert_ok_response(state_data)

    assert "call" in state_data
    assert state_data["call"]["call_id"] == call_id
    assert state_data["call"]["status"] == "active"
    assert "phase" in state_data["call"]
    assert "turn_count" in state_data["call"]
    assert "last_seen_at" in state_data["call"]

    end_response = api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": call_id,
        },
    )
    end_data = assert_json_response(end_response)
    assert_ok_response(end_data)

    assert end_data["call_id"] == call_id
    assert end_data["status"] == "ended"
    assert end_data["phase"] == "completed"
    assert "call" in end_data
    assert end_data["call"]["status"] == "ended"
    assert end_data["call"]["phase"] == "completed"
    assert end_data["call"]["ended_at"]

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