import logging

from aiagent.perception.asr_listener import ASRListener
from aiagent.perception.voice_session_controller import VoiceSessionController
from aiagent.state.stream_state import StreamingState
from integrations.asr.microphone import StreamingMicrophone


class VoiceTurnManager:
    def __init__(
        self,
        asr_listener: ASRListener,
        microphone: StreamingMicrophone,
        stream_state: StreamingState,
        session_controller:VoiceSessionController
    ) -> None:
        self.asr_listener = asr_listener
        self.microphone = microphone
        self.stream_state = stream_state
        self.session_controller = session_controller    
        self.logger = logging.getLogger(self.__class__.__name__)

    def capture_turn(
        self,
        max_seconds: float = 8.0,
        silence_seconds: float = 1.2,
        interrupt_playback:bool = True
    ) -> str:
        self.session_controller.prepare_for_listening(
            interrupt_playback=interrupt_playback,
        )
        self.stream_state.is_processing_voice = False

        try:
            audio_path = self.microphone.record_until_silence(
                max_seconds=max_seconds,
                silence_seconds=silence_seconds,
            )
            self.stream_state.last_recording_path = audio_path

            self.stream_state.is_listening = False
            self.stream_state.is_processing_voice = True

            transcript = self.asr_listener.transcribe_file(audio_path)
            self.stream_state.last_transcript = transcript

            self.logger.info("Voice turn transcript: %s", transcript)
            return transcript

        except Exception as exc:
            self.stream_state.last_error = str(exc)
            raise

        finally:
            self.stream_state.is_listening = False
            self.stream_state.is_processing_voice = False
            self.session_controller.finish_listening()