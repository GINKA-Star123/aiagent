"""Microphone and ASR input adapter."""

from aiagent.schemas.inputs import InputEvent,InputSource
from integrations.asr.mock_asr_client import MockASRClient

class ASRListener:
    def __init__(self,asr_client:MockASRClient) ->None:
        self.asr_client = asr_client

    def transcribe_to_event(self,audio_text:str,user_id :str="mic",username:str = "麦克风输入") ->InputEvent:
        text = self.asr_client.transcribe(audio_text=audio_text)
        return InputEvent(
            source=InputSource.ASR,
            user_id=user_id,
            user_name=username,
            text=text
        )