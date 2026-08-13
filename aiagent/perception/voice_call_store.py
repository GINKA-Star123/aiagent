from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from aiagent.schemas.voice import VoiceCallStatus, VoiceRealtimeCall, VoiceTurnPhase


class VoiceRealtimeCallStore:
    def __init__(self, ttl_seconds: float = 1800.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._calls: dict[str, VoiceRealtimeCall] = {}

    def start(self, *, user_id: str, username: str) -> VoiceRealtimeCall:
        self._cleanup_expired()

        call_id = uuid.uuid4().hex
        call = VoiceRealtimeCall(
            call_id=call_id,
            user_id=user_id or "guest",
            username=username or "guest",
        )
        self._calls[call_id] = call
        return call

    def get(self, call_id: str) -> VoiceRealtimeCall | None:
        self._cleanup_expired()
        call = self._calls.get(call_id)
        if call is None:
            return None

        call.touch()
        return call

    def mark_phase(
        self,
        call_id: str,
        phase: VoiceTurnPhase,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.mark_phase(phase, **metadata)
        return call

    def next_turn(self, call_id: str) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.turn_count += 1
        call.last_turn_id = f"{call.call_id}:{call.turn_count}"
        call.last_error = ""
        call.last_transcript = ""
        call.last_output_id = ""
        call.last_audio_path = ""
        call.last_audio_url = ""
        call.last_interrupt_reason = ""

        call.update_metadata(
            voice_realtime_call_id=call.call_id,
            voice_realtime_turn_id=call.last_turn_id,
            voice_realtime_turn_count=call.turn_count,
        )
        call.mark_phase(VoiceTurnPhase.UPLOADED)
        return call

    def mark_transcript(
        self,
        call_id: str,
        transcript: str,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        normalized = transcript.strip()
        call.last_transcript = normalized

        phase = VoiceTurnPhase.THINKING if normalized else VoiceTurnPhase.EMPTY_TURN
        call.mark_phase(
            phase,
            **{
                **metadata,
                "voice_asr_text_chars": len(normalized),
                "voice_asr_empty": not bool(normalized),
            },
        )
        return call

    def mark_output(
        self,
        call_id: str,
        *,
        output_id: str,
        audio_path: str = "",
        audio_url: str = "",
        has_audio: bool | None = None,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.last_output_id = output_id
        call.last_audio_path = audio_path or ""
        call.last_audio_url = audio_url or ""

        output_has_audio = has_audio if has_audio is not None else bool(audio_path or audio_url)
        phase = VoiceTurnPhase.SPEAKING if output_has_audio else VoiceTurnPhase.COMPLETED

        call.mark_phase(
            phase,
            **{
                **metadata,
                "voice_output_id": output_id,
                "voice_audio_path": audio_path or "",
                "voice_audio_url": audio_url or "",
                "voice_output_has_audio": output_has_audio,
            },
        )
        return call

    def interrupt(
        self,
        call_id: str,
        reason: str,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        interrupt_reason = reason or "voice_realtime_interrupt"
        call.interrupt_count += 1
        call.last_interrupt_reason = interrupt_reason
        call.mark_phase(
            VoiceTurnPhase.INTERRUPTED,
            **{
                **metadata,
                "voice_interrupt_reason": interrupt_reason,
                "voice_interrupt_count": call.interrupt_count,
            },
        )
        return call

    def fail(
        self,
        call_id: str,
        error: Exception | str,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.status = VoiceCallStatus.ERROR
        call.last_error = str(error)
        call.mark_phase(
            VoiceTurnPhase.FAILED,
            **{
                **metadata,
                "voice_last_error": str(error),
            },
        )
        return call

    def end(self, call_id: str) -> VoiceRealtimeCall:
        call = self._calls.pop(call_id, None)
        if call is None:
            call = VoiceRealtimeCall(call_id=call_id)

        call.status = VoiceCallStatus.ENDED
        call.ended_at = datetime.now().isoformat(timespec="seconds")
        call.mark_phase(
            VoiceTurnPhase.COMPLETED,
            voice_call_ended=True,
        )
        return call

    def _cleanup_expired(self) -> None:
        if self.ttl_seconds <= 0:
            return

        now = time.time()
        expired: list[str] = []

        for call_id, call in self._calls.items():
            try:
                last_seen = datetime.fromisoformat(call.last_seen_at).timestamp()
            except Exception:
                last_seen = now

            if now - last_seen > self.ttl_seconds:
                expired.append(call_id)

        for call_id in expired:
            self._calls.pop(call_id, None)