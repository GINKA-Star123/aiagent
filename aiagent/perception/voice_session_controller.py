import logging
from datetime import datetime

from aiagent.expression.audio_playback_dispatcher import AudioPlaybackDispatcher
from aiagent.state.speaking_state import SpeakingState
from aiagent.state.stream_state import StreamingState


class VoiceSessionController:
    def __init__(
            self,
            audio_playback_dispatcher: AudioPlaybackDispatcher,
            speaking_state: SpeakingState,
            streaming_state: StreamingState,
    ) -> None:
        self.audio_playback_dispatcher = audio_playback_dispatcher
        self.speaking_state = speaking_state
        self.streaming_state = streaming_state
        self.logger = logging.getLogger(self.__class__.__name__)

    def prepare_for_listening(self,interrupt_playback:bool = True) -> None:
        self.audio_playback_dispatcher.refresh_state()

        if interrupt_playback and self.speaking_state.is_speaking:
            self.logger.info("Interrupting current playback before listening")
            self.audio_playback_dispatcher.interrupt(reason="listen_start")

        self.streaming_state.is_listening = True  
        self.streaming_state.last_error = ""
        self.streaming_state.is_processing_voice = False
        self.streaming_state.last_session_status = "listening"
        self.streaming_state.last_updated_at=datetime.now().isoformat(timespec="seconds")

    def finish_listening(self)->None:
        self.streaming_state.is_listening = False
        self.streaming_state.is_processing_voice = False
        self.streaming_state.last_session_status = "idle"
        self.streaming_state.last_updated_at = datetime.now().isoformat(timespec="seconds")

    def interrupt_listening(self,reason:str = "voice-session-interrupt")->None:
        self.audio_playback_dispatcher.interrupt(reason=reason)
        self.streaming_state.is_listening = False
        self.streaming_state.is_processing_voice = False
        self.streaming_state.last_interrupt_reason = reason
        self.streaming_state.last_session_status = "interrupted"
        self.streaming_state.last_updated_at = datetime.now().isoformat(timespec="seconds")

    def mark_processing(self)->None:
        self.streaming_state.is_processing_voice = True
        self.streaming_state.last_session_status = "processing_voice"
        self.streaming_state.last_updated_at = datetime.now().isoformat(timespec="seconds")

    def finish_processing(self,transcirpt:str = "") ->None:
        self.streaming_state.is_listening = False
        self.streaming_state.last_transcript =transcirpt
        self.streaming_state.last_session_status = "completed"
        self.streaming_state.last_updated_at = datetime.now().isoformat(timespec="seconds")



    