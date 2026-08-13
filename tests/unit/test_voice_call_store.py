from aiagent.perception.voice_call_store import VoiceRealtimeCallStore
from aiagent.schemas.voice import VoiceCallStatus, VoiceTurnPhase


def test_voice_call_store_start_and_get():
    store = VoiceRealtimeCallStore()

    call = store.start(user_id="u1", username="tester")
    loaded = store.get(call.call_id)

    assert loaded is not None
    assert loaded.call_id == call.call_id
    assert loaded.user_id == "u1"
    assert loaded.username == "tester"
    assert loaded.status == VoiceCallStatus.ACTIVE
    assert loaded.phase == VoiceTurnPhase.IDLE


def test_voice_call_store_turn_flow():
    store = VoiceRealtimeCallStore()
    call = store.start(user_id="u1", username="tester")

    call = store.next_turn(call.call_id)
    assert call is not None
    assert call.turn_count == 1
    assert call.last_turn_id.endswith(":1")
    assert call.phase == VoiceTurnPhase.UPLOADED
    assert call.metadata["voice_realtime_phase"] == "uploaded"
    assert call.metadata["voice_realtime_status"] == "active"

    call = store.mark_phase(call.call_id, VoiceTurnPhase.TRANSCRIBING)
    assert call is not None
    assert call.phase == VoiceTurnPhase.TRANSCRIBING

    call = store.mark_transcript(call.call_id, "你好")
    assert call is not None
    assert call.last_transcript == "你好"
    assert call.phase == VoiceTurnPhase.THINKING
    assert call.metadata["voice_asr_empty"] is False
    assert call.metadata["voice_realtime_phase"] == "thinking"

    call = store.mark_output(
        call.call_id,
        output_id="out_1",
        audio_path="data/audio/out.wav",
        audio_url="/audio/out.wav",
    )
    assert call is not None
    assert call.last_output_id == "out_1"
    assert call.phase == VoiceTurnPhase.SPEAKING


def test_voice_call_store_empty_turn():
    store = VoiceRealtimeCallStore()
    call = store.start(user_id="u1", username="tester")
    store.next_turn(call.call_id)

    call = store.mark_transcript(call.call_id, "")

    assert call is not None
    assert call.phase == VoiceTurnPhase.EMPTY_TURN
    assert call.last_transcript == ""
    assert call.metadata["voice_asr_empty"] is True


def test_voice_call_store_interrupt_and_end():
    store = VoiceRealtimeCallStore()
    call = store.start(user_id="u1", username="tester")

    call = store.interrupt(call.call_id, "unit_interrupt")
    assert call is not None
    assert call.phase == VoiceTurnPhase.INTERRUPTED
    assert call.interrupt_count == 1
    assert call.last_interrupt_reason == "unit_interrupt"
    assert call.metadata["voice_realtime_phase"] == "interrupted"

    ended = store.end(call.call_id)
    assert ended.status == VoiceCallStatus.ENDED
    assert ended.phase == VoiceTurnPhase.COMPLETED
    assert ended.ended_at
    assert store.get(call.call_id) is None


def test_voice_call_store_fail_marks_error_state():
    store = VoiceRealtimeCallStore()
    call = store.start(user_id="u1", username="tester")

    call = store.fail(call.call_id, RuntimeError("boom"))

    assert call is not None
    assert call.status == VoiceCallStatus.ERROR
    assert call.phase == VoiceTurnPhase.FAILED
    assert call.last_error == "boom"
    assert call.metadata["voice_realtime_status"] == "error"
    assert call.metadata["voice_realtime_phase"] == "failed"