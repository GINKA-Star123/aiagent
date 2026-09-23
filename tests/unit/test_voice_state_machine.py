from __future__ import annotations

from aiagent.perception.voice_state_machine import (
    MAX_INTERRUPT_REASON_LENGTH,
    can_interrupt,
    can_start_turn,
    normalize_interrupt_reason,
)
from aiagent.schemas.voice import (
    VoiceCallStatus,
    VoiceRealtimeCall,
    VoiceTurnPhase,
)


def _call(
    *,
    status: VoiceCallStatus = VoiceCallStatus.ACTIVE,
    phase: VoiceTurnPhase = VoiceTurnPhase.IDLE,
) -> VoiceRealtimeCall:
    return VoiceRealtimeCall(
        call_id="call-1",
        user_id="user-1",
        username="tester",
        status=status,
        phase=phase,
    )


def test_idle_call_can_start_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.IDLE)
    )

    assert decision.allowed is True
    assert decision.reason == ""
    assert decision.current_phase == "idle"
    assert decision.current_status == "active"


def test_completed_call_can_start_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.COMPLETED)
    )

    assert decision.allowed is True


def test_empty_turn_can_start_next_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.EMPTY_TURN)
    )

    assert decision.allowed is True


def test_interrupted_call_can_start_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.INTERRUPTED)
    )

    assert decision.allowed is True


def test_uploaded_call_cannot_start_second_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.UPLOADED)
    )

    assert decision.allowed is False
    assert decision.reason == "turn_already_uploaded"


def test_transcribing_call_cannot_start_second_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.TRANSCRIBING)
    )

    assert decision.allowed is False
    assert decision.reason == "transcription_in_progress"


def test_thinking_call_cannot_start_second_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.THINKING)
    )

    assert decision.allowed is False
    assert decision.reason == "thinking_in_progress"


def test_speaking_call_requires_interrupt_before_new_turn():
    decision = can_start_turn(
        _call(phase=VoiceTurnPhase.SPEAKING)
    )

    assert decision.allowed is False
    assert decision.reason == "interrupt_required"
    assert "interrupt" in decision.message


def test_ended_call_cannot_start_turn():
    decision = can_start_turn(
        _call(
            status=VoiceCallStatus.ENDED,
            phase=VoiceTurnPhase.COMPLETED,
        )
    )

    assert decision.allowed is False
    assert decision.reason == "call_ended"


def test_failed_call_cannot_start_turn():
    decision = can_start_turn(
        _call(
            status=VoiceCallStatus.ERROR,
            phase=VoiceTurnPhase.FAILED,
        )
    )

    assert decision.allowed is False
    assert decision.reason == "call_failed"


def test_active_call_can_interrupt():
    decision = can_interrupt(
        _call(phase=VoiceTurnPhase.SPEAKING)
    )

    assert decision.allowed is True


def test_ended_call_cannot_interrupt():
    decision = can_interrupt(
        _call(
            status=VoiceCallStatus.ENDED,
            phase=VoiceTurnPhase.COMPLETED,
        )
    )

    assert decision.allowed is False
    assert decision.reason == "call_ended"


def test_failed_call_cannot_interrupt():
    decision = can_interrupt(
        _call(
            status=VoiceCallStatus.ERROR,
            phase=VoiceTurnPhase.FAILED,
        )
    )

    assert decision.allowed is False
    assert decision.reason == "call_failed"


def test_empty_interrupt_reason_uses_default():
    assert (
        normalize_interrupt_reason("")
        == "voice_realtime_interrupt"
    )
    assert (
        normalize_interrupt_reason(None)
        == "voice_realtime_interrupt"
    )


def test_interrupt_reason_is_truncated():
    reason = "x" * 1000

    normalized = normalize_interrupt_reason(reason)

    assert len(normalized) == MAX_INTERRUPT_REASON_LENGTH
    assert normalized == "x" * MAX_INTERRUPT_REASON_LENGTH