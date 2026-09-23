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

def test_voice_realtime_turn_rejects_when_playback_is_speaking(
    api_client,
    test_user,
    tmp_path,
):
    call_id = _start_call(api_client, test_user)

    runtime = get_runtime()
    runtime_call = runtime.handle_chat_full(
        text="先生成一条语音回复",
        user_id=test_user["user_id"],
        username=test_user["username"],
    )

    call_state_response = api_client.get(
        f"/voice/realtime/state/{call_id}",
    )
    call_state = assert_json_response(call_state_response)

    assert call_state["phase"] == "idle"

    start_turn_audio = tmp_path / "first-turn.m4a"
    start_turn_audio.write_bytes(b"first mock audio")

    with start_turn_audio.open("rb") as file_obj:
        first_response = api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": call_id,
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={
                "file": (
                    "first-turn.m4a",
                    file_obj,
                    "audio/mp4",
                ),
            },
        )

    first_data = assert_json_response(first_response)

    if first_data.get("phase") != "speaking":
        return

    second_audio = tmp_path / "second-turn.m4a"
    second_audio.write_bytes(b"second mock audio")

    with second_audio.open("rb") as file_obj:
        second_response = api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": call_id,
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={
                "file": (
                    "second-turn.m4a",
                    file_obj,
                    "audio/mp4",
                ),
            },
        )

    second_data = assert_json_response(
        second_response,
        expected_status=409,
    )

    assert_error_response(
        second_data,
        stage="voice_realtime_state_conflict",
    )
    assert second_data["state_reason"] == "interrupt_required"
    assert second_data["current_phase"] == "speaking"

def test_voice_realtime_turn_rejects_during_processing(
    api_client,
    test_user,
    monkeypatch,
    tmp_path,
):
    call_id = _start_call(api_client, test_user)

    from apps.api.routes.voice_realtime import _CALL_STORE
    from aiagent.schemas.voice import VoiceTurnPhase

    # 这些 store 方法都是 async，且共享一把绑定在 app 事件循环上的 asyncio.Lock，
    # 所以必须通过 TestClient 的 portal 在同一个 loop 上执行，
    # 不能用 asyncio.run（会报 "bound to a different event loop"）。
    portal = api_client.portal
    assert portal is not None

    call = portal.call(_CALL_STORE.next_turn, call_id)
    assert call is not None

    portal.call(
        _CALL_STORE.mark_phase,
        call_id,
        VoiceTurnPhase.THINKING,
    )

    # 回读校验：确认 phase 真的进入了 thinking，避免"静默没生效"
    seeded_call = portal.call(_CALL_STORE.get, call_id)
    assert seeded_call is not None
    assert seeded_call.phase == VoiceTurnPhase.THINKING

    audio_path = tmp_path / "duplicate-turn.m4a"
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
                "file": (
                    "duplicate-turn.m4a",
                    file_obj,
                    "audio/mp4",
                ),
            },
        )

    data = assert_json_response(
        response,
        expected_status=409,
    )

    assert_error_response(
        data,
        stage="voice_realtime_state_conflict",
    )
    assert data["state_reason"] == "thinking_in_progress"
    assert data["current_phase"] == "thinking"
    assert data["current_status"] == "active"

def test_voice_realtime_turn_rejects_empty_audio(
    api_client,
    test_user,
    tmp_path,
):
    call_id = _start_call(api_client, test_user)

    audio_path = tmp_path / "empty-audio.m4a"
    audio_path.write_bytes(b"")

    with audio_path.open("rb") as file_obj:
        response = api_client.post(
            "/voice/realtime/turn",
            data={
                "call_id": call_id,
                "user_id": test_user["user_id"],
                "username": test_user["username"],
            },
            files={
                "file": (
                    "empty-audio.m4a",
                    file_obj,
                    "audio/mp4",
                ),
            },
        )

    data = assert_json_response(
        response,
        expected_status=400,
    )

    assert_error_response(
        data,
        stage="voice_upload_validation",
    )
    assert data["call_id"] == call_id

def test_voice_realtime_interrupt_reason_is_bounded(
    api_client,
    test_user,
):
    call_id = _start_call(api_client, test_user)

    response = api_client.post(
        "/voice/realtime/interrupt",
        json={
            "call_id": call_id,
            "reason": "x" * 1000,
        },
    )

    data = assert_json_response(response)

    assert data["ok"] is True
    assert len(data["metadata"]["voice_interrupt_reason"]) <= 120
    assert len(data["call"]["last_interrupt_reason"]) <= 120

def test_voice_realtime_turn_rejects_ended_call(
    api_client,
    test_user,
    tmp_path,
):
    call_id = _start_call(api_client, test_user)

    end_response = api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": call_id,
        },
    )

    end_data = assert_json_response(end_response)
    assert end_data["status"] == "ended"

    audio_path = tmp_path / "ended-call.m4a"
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
                "file": (
                    "ended-call.m4a",
                    file_obj,
                    "audio/mp4",
                ),
            },
        )

    data = assert_json_response(
        response,
        expected_status=404,
    )

    assert_error_response(
        data,
        stage="voice_realtime_turn",
    )


def test_voice_realtime_end_missing_call_contract(api_client):
    response = api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": "missing-call-id",
        },
    )

    data = assert_json_response(
        response,
        expected_status=404,
    )

    assert_error_response(
        data,
        stage="voice_realtime_end",
    )


def test_voice_realtime_end_is_idempotent(api_client, test_user):
    call_id = _start_call(api_client, test_user)

    first_response = api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": call_id,
        },
    )
    first = assert_json_response(first_response)

    second_response = api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": call_id,
        },
    )
    second = assert_json_response(second_response)

    assert first["status"] == "ended"
    assert second["status"] == "ended"
    assert first["call_id"] == call_id
    assert second["call_id"] == call_id
    assert first["call"]["ended_at"]
    assert second["call"]["ended_at"]


def test_voice_realtime_ended_state_remains_queryable(
    api_client,
    test_user,
):
    call_id = _start_call(api_client, test_user)

    api_client.post(
        "/voice/realtime/end",
        json={
            "call_id": call_id,
        },
    )

    response = api_client.get(
        f"/voice/realtime/state/{call_id}",
    )
    data = assert_json_response(response)

    assert_voice_realtime_response_contract(data)
    assert data["call_id"] == call_id
    assert data["status"] == "ended"
    assert data["phase"] == "completed"