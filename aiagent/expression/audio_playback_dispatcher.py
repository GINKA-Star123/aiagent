from __future__ import annotations

from datetime import datetime
from pathlib import Path

from aiagent.schemas.outputs import ResponsePacket
from aiagent.state.speaking_state import SpeakingState
from integrations.audio.audio_player import AudioPlayer


class AudioPlaybackDispatcher:
    def __init__(
        self,
        audio_player: AudioPlayer,
        speaking_state: SpeakingState,
    ) -> None:
        self.audio_player = audio_player
        self.speaking_state = speaking_state

    def dispatch(self, packet: ResponsePacket) -> ResponsePacket:
        self.refresh_state()

        if not packet.audio_path:
            packet.metadata["audio_playback"] = "skipped_no_audio"
            return packet

        audio_path = Path(packet.audio_path)
        suffix = audio_path.suffix.lower()

        if suffix not in {".wav", ".mp3", ".ogg"}:
            packet.metadata["audio_playback"] = f"skipped_non_audio:{suffix or 'no_suffix'}"
            return packet

        self.speaking_state.is_speaking = True
        self.speaking_state.current_text = packet.reply_text
        self.speaking_state.current_audio_path = str(audio_path)
        self.speaking_state.last_audio_path = str(audio_path)
        self.speaking_state.playback_status = "starting"
        self.speaking_state.is_interrupted = False
        self.speaking_state.last_stop_reason = ""
        self.speaking_state.playback_started_at = datetime.now().isoformat(timespec="seconds")
        self.speaking_state.playback_finished_at = ""
        self.speaking_state.last_updated_at = datetime.now().isoformat(timespec="seconds")

        try:
            self.speaking_state.audio_duration_sec =self.audio_player.get_duration_seconds(str(audio_path))
        except Exception:
            self.speaking_state.audio_duration_sec = 0.0

        try:
            self.audio_player.play_async(str(audio_path))
            self.speaking_state.playback_status = "playing"
            packet.metadata["audio_playback"] = "started_async"
        except Exception as exc:
            self.speaking_state.is_speaking = False
            self.speaking_state.playback_status = "failed"
            self.speaking_state.last_stop_reason = str(exc)
            self.speaking_state.playback_finished_at = datetime.now().isoformat(timespec="seconds")
            self.speaking_state.last_updated_at = datetime.now().isoformat(timespec="seconds")
            packet.metadata["audio_playback"] = f"failed:{exc}"

        return packet

    def interrupt(self,reason: str = "manual_interrupt")->None:
        self.audio_player.stop()
        self.speaking_state.is_speaking = False
        self.speaking_state.playback_status = "interrupted"
        self.speaking_state.is_interrupted = True
        self.speaking_state.last_stop_reason = reason
        self.speaking_state.playback_finished_at = datetime.now().isoformat(timespec="seconds")
        self.speaking_state.last_updated_at = datetime.now().isoformat(timespec="seconds")

    def refresh_state(self) ->None:
        now = datetime.now().isoformat(timespec="seconds")

        if self.audio_player.is_busy():
            self.speaking_state.playback_status = "playing"
            self.speaking_state.is_speaking = True
            self.speaking_state.last_updated_at =now
            return
        
        if self.speaking_state.playback_status in {"playing", "starting"}:
            self.speaking_state.is_speaking = False
            self.speaking_state.playback_status = "completed"
            self.speaking_state.current_audio_path = ""
            self.speaking_state.current_text = ""
            self.speaking_state.playback_finished_at =now
            self.speaking_state.last_updated_at=now