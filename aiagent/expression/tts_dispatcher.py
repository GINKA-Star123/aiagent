"""Dispatch text to TTS service."""
from aiagent.schemas.outputs import ResponsePacket
from aiagent.state.speaking_state import SpeakingState
from integrations.tts.mock_tts_client import MockTTSClient

class TTSDispatcher:
    def __init__(self,tts_client: MockTTSClient,speaking_state: SpeakingState) -> None:
        self.tts_client = tts_client
        self.speaking_state = speaking_state
    
    def dispatch(self,packet:ResponsePacket)  -> ResponsePacket:

        if not packet.should_speak:
            return packet
        
        self.speaking_state.is_speaking = True
        self.speaking_state.current_text = packet.reply_text

        audio_path = self.tts_client.synthesize(packet.reply_text)

        self.speaking_state.last_audio_path = audio_path
        self.speaking_state.is_speaking = False

        packet.audio_path = audio_path
        packet.metadata["tts"] = "mock"
        return packet