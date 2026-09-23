from __future__ import annotations

from dataclasses import dataclass

from aiagent.schemas.voice import VoiceCallStatus,VoiceRealtimeCall,VoiceTurnPhase

MAX_INTERRUPT_REASON_LENGTH = 120

@dataclass(frozen=True)
class VoiceStateDecision:
    """
    Voice realtime 状态判断结果

    allowed:
        当前操作是否允许执行

    reason:
        不允许执行时的机器可读原因

    message:
        可以直接返回给API客户端的稳定错误描述

    current_phase:
        当前通话阶段

    current_status:
        当前通话状态

    """

    allowed:bool
    reason: str = ""
    message: str = ""
    current_phase: str = ""
    current_status: str = ""

    def as_dict(self) -> dict[str,str|bool]:
        """
        转换为API extra 字段
        """

        return {
            "allowed":self.allowed,
            "reason":self.reason,
            "message":self.message,
            "current_phase":self.current_phase,
            "current_status":self.current_status,
        }

def _phase_value(call: VoiceRealtimeCall) -> str:
    value = getattr(call.phase, "value", call.phase)
    return str(value)

def _status_value(call: VoiceRealtimeCall) -> str:
    value = getattr(call.status,"value",call.status)
    return str(value)

def _decision(
    call: VoiceRealtimeCall,
    *,
    allowed: bool,
    reason: str = "",
    message: str = "",
) -> VoiceStateDecision:
    return VoiceStateDecision(
        allowed=allowed,
        reason=reason,
        message=message,
        current_phase=_phase_value(call),
        current_status=_status_value(call),
    )

def normalize_interrupt_reason(reason: str | None) -> str:
    """
    规范化打断原因

    空原因使用统一默认值
    过长原因截断,避免客户端将大段文本写入metadata和日志
    """

    normalized = (reason or "").strip()

    if not normalized:
        normalized = "voice_realtime_interrupt"

    return normalized[:MAX_INTERRUPT_REASON_LENGTH]

def can_start_turn(call: VoiceRealtimeCall) -> VoiceStateDecision:
    """
    判断当前通话是否允许开始新的语音turn

    允许开始新turn的阶段:

    - idle: 通话刚建立,还没有开始turn
    - completed: 上一轮已经完成
    - empty_turn: 上一轮没有识别出文本
    - interrupted: 上一轮被打断

    以下阶段不允许直接开始新的turn:

    - uploaded
    - transcribing
    - thinking
    - speaking

    speaking阶段必须先调用interrupt
    这样可以明确记录用户打断了当前播放

    """

    if call.status == VoiceCallStatus.ENDED:
        return _decision(
            call,
            allowed=False,
            reason="call_ended",
            message="call has already ended",
        )

    if call.status == VoiceCallStatus.ERROR:
        return _decision(
            call,
            allowed=False,
            reason="call_failed",
            message="call is in failed state",
        )

    allowed_phases = {
        VoiceTurnPhase.IDLE,
        VoiceTurnPhase.COMPLETED,
        VoiceTurnPhase.EMPTY_TURN,
        VoiceTurnPhase.INTERRUPTED,
    }

    if call.phase in allowed_phases:
        return _decision(call,allowed=True)

    if call.phase == VoiceTurnPhase.SPEAKING:
        return _decision(
            call,
            allowed=False,
            reason="interrupt_required",
            message="interrupt current playback before starting a new turn",
        )

    if call.phase == VoiceTurnPhase.UPLOADED:
        return _decision(
            call,
            allowed=False,
            reason="turn_already_uploaded",
            message="current turn is already being processed",
        )

    if call.phase == VoiceTurnPhase.TRANSCRIBING:
        return _decision(
            call,
            allowed=False,
            reason="transcription_in_progress",
            message="transcription is still in progress",
        )

    if call.phase == VoiceTurnPhase.THINKING:
        return _decision(
            call,
            allowed=False,
            reason="thinking_in_progress",
            message="response generation is still in progress",
        )

    return _decision(
        call,
        allowed=False,
        reason="invalid_call_phase",
        message="current call phase does not accept a new turn",
    )

def can_interrupt(call:VoiceRealtimeCall) -> VoiceStateDecision:
    """
    判断当前通话是否允许执行打断

    active通话允许interrupt
    已经结束和已经失败的通话不能继续打断
    """

    if call.status == VoiceCallStatus.ENDED:
        return _decision(
            call,
            allowed=False,
            reason="call_ended",
            message="call has already ended",
        )

    if call.status == VoiceCallStatus.ERROR:
        return _decision(
            call,
            allowed=False,
            reason="call_failed",
            message="call is in failed state",
        )

    return _decision(call,allowed=True)

def can_end(call: VoiceRealtimeCall) -> VoiceStateDecision:
    """
    判断当前通话是否允许结束

    active 通话可以结束
    ended 通话返回幂等允许结果
    error 通话也允许执行清理结束
    """

    return _decision(call,allowed=True)

def state_conflict_extra(
        decision: VoiceStateDecision,
) -> dict[str,str|bool]:
    """
    将状态冲突转成统一API响应中的extra字段
    """

    return {
        "state_reason":decision.reason,
        "current_phase":decision.current_phase,
        "current_status":decision.current_status,
    }