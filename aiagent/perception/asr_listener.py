"""Microphone and ASR input adapter."""
import logging

from integrations.asr.faster_whisper_client import FasterWhisperClient
from integrations.asr.mock_asr_client import MockASRClient
from integrations.audio.microphone_recorder import MicrophoneRecorder


class ASRListener:
    def __init__(
            self,
            asr_client: MockASRClient | FasterWhisperClient,
            recorder: MicrophoneRecorder | None = None,
            asr_provider : str = "mock",
            enable_mock_asr : bool =True,
    ) -> None:
        self.asr_client = asr_client
        self.recorder = recorder
        self.asr_provider = asr_provider
        self.enable_mock_asr = enable_mock_asr
        self.logger = logging.getLogger(self.__class__.__name__)

    def transcribe_file(self,audio_path :str) ->str:
        self.logger.info("ASR transcribing file: %s", audio_path)
        return self.asr_client.transcribe(audio_path)
    
    def listen_once(self,record_seconds:int =10) ->str:
        if self.enable_mock_asr or self.asr_provider == "mock":
            self.logger.info("Using mock ASR mode.")
            return self.asr_client.transcribe("mock audio")
        
        if self.recorder is None:
            raise RuntimeError("Microphone recorder is not initialized")
        
        audio_path = self.recorder.record(record_seconds)
        self.logger.info("Microphone recording saved: %s", audio_path)
        return self.asr_client.transcribe(audio_path)