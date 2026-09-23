from __future__ import annotations

from tests.helpers.api_contract import assert_json_response, assert_ok_response


def _start_call(api_client, test_user) -> str:
    response = api_client.post(
        "/voice/realtime/start",
        json={
            "user_id": test_user["user_id"],
            "username": test_user["username"],
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)

    return data["call_id"]


def _post_turn(api_client, test_user, call_id: str, tmp_path, name: str):
    audio_path = tmp_path / name
    audio_path.write_bytes(b"mock voice bytes")

    with audio_path.open("rb") as file_obj:
        return api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": call_id,
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={"file": (name, file_obj, "audio/mp4")},
        )


def test_voice_turn_reports_session_and_turn_id(api_client, test_user, tmp_path):
    call_id = _start_call(api_client, test_user)

    data = assert_json_response(_post_turn(api_client, test_user, call_id, tmp_path, "t1.m4a"))

    assert data["call_id"] == call_id
    assert data["session_id"] == call_id
    assert data["turn_id"] == f"{call_id}:1"

    metadata = data["metadata"]
    assert metadata["voice_realtime_session_id"] == call_id
    assert metadata["voice_realtime_turn_id"] == f"{call_id}:1"
    assert metadata["session_id"] == call_id
    assert metadata["turn_id"] == f"{call_id}:1"


def test_voice_turn_reports_stage_latency_metadata(api_client, test_user, tmp_path):
    call_id = _start_call(api_client, test_user)

    data = assert_json_response(_post_turn(api_client, test_user, call_id, tmp_path, "t2.m4a"))
    metadata = data["metadata"]

    for key in (
        "voice_upload_latency_ms",
        "voice_asr_latency_ms",
        "voice_chat_latency_ms",
        "voice_turn_latency_ms",
    ):
        assert key in metadata, f"missing voice stage latency: {key}"

    assert metadata["voice_tts_status"] in {"done", "skipped"}
    assert "voice_tts_latency_ms" in metadata
    assert metadata["voice_llm_latency_ms"]
    assert metadata["voice_live2d_status"] in {"ok", "skipped"}


def test_voice_second_turn_requires_interrupt(api_client, test_user, tmp_path):
    call_id = _start_call(api_client, test_user)

    first = assert_json_response(_post_turn(api_client, test_user, call_id, tmp_path, "t3.m4a"))
    assert first["turn_id"] == f"{call_id}:1"

    if first["phase"] != "speaking":
        # mock TTS 未产出音频时会直接 completed，此时无需打断即可进入下一轮
        second = assert_json_response(_post_turn(api_client, test_user, call_id, tmp_path, "t4.m4a"))
        assert second["turn_id"] == f"{call_id}:2"
        return

    conflict = api_client.post(
        "/voice/realtime/turn",
        data={
            "call_id": call_id,
            "user_id": test_user["user_id"],
            "username": test_user["username"],
        },
        files={"file": ("t5.m4a", b"mock voice bytes", "audio/mp4")},
    )
    conflict_data = assert_json_response(conflict, expected_status=409)
    assert conflict_data["state_reason"] == "interrupt_required"

    interrupt = api_client.post(
        "/voice/realtime/interrupt",
        json={"call_id": call_id, "reason": "unit_interrupt"},
    )
    assert_json_response(interrupt)

    second = assert_json_response(_post_turn(api_client, test_user, call_id, tmp_path, "t6.m4a"))
    assert second["turn_id"] == f"{call_id}:2"
    assert second["metadata"]["voice_realtime_turn_count"] == 2