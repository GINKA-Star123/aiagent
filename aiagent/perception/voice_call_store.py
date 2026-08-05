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
        call.mark_phase(VoiceTurnPhase.UPLOADED)
        return call

    def mark_transcript(self, call_id: str, transcript: str) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.last_transcript = transcript.strip()
        call.mark_phase(
            VoiceTurnPhase.EMPTY_TURN if not call.last_transcript else VoiceTurnPhase.THINKING
        )
        return call

    def mark_output(
        self,
        call_id: str,
        *,
        output_id: str,
        audio_path: str = "",
        audio_url: str = "",
    ) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.last_output_id = output_id
        call.last_audio_path = audio_path or ""
        call.last_audio_url = audio_url or ""

        if audio_path or audio_url:
            call.mark_phase(VoiceTurnPhase.SPEAKING)
        else:
            call.mark_phase(VoiceTurnPhase.COMPLETED)

        return call

    def interrupt(self, call_id: str, reason: str) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.interrupt_count += 1
        call.last_interrupt_reason = reason or "voice_realtime_interrupt"
        call.mark_phase(VoiceTurnPhase.INTERRUPTED)
        return call

    def fail(self, call_id: str, error: Exception | str) -> VoiceRealtimeCall | None:
        call = self.get(call_id)
        if call is None:
            return None

        call.status = VoiceCallStatus.ERROR
        call.last_error = str(error)
        call.mark_phase(VoiceTurnPhase.FAILED)
        return call

    def end(self, call_id: str) -> VoiceRealtimeCall:
        call = self._calls.pop(call_id, None)
        if call is None:
            call = VoiceRealtimeCall(call_id=call_id)

        call.status = VoiceCallStatus.ENDED
        call.phase = VoiceTurnPhase.COMPLETED
        call.ended_at = datetime.now().isoformat(timespec="seconds")
        call.touch()
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