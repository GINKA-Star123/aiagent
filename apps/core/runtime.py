"""Runtime lifecycle management for the core application."""
from aiagent.orchestrator.dispatcher import EventDispatcher
from aiagent.perception.asr_listener import ASRListener
from aiagent.schemas.inputs import InputEvent, InputSource
from aiagent.schemas.outputs import OutputEvent
from aiagent.state.speaking_state import SpeakingState

class CoreRuntime:
    def __init__(self, dispatcher: EventDispatcher, speaking_state: SpeakingState,asr_listener: ASRListener) -> None:
        self.dispatcher = dispatcher
        self.speaking_state = speaking_state
        self.asr_listener = asr_listener    

    def handle_chat(self,text:str,user_id : str="guest",username:str ="guest") ->str:
        event = InputEvent(
            source=InputSource.CHAT,
            text=text,
            user_id=user_id,
            user_name=username,
        )
        output = self.dispatcher.handle_input(event)
        return output.packet.reply_text
    
    def handle_chat_full(self, text: str, user_id: str = "guest", username: str = "guest") -> OutputEvent:
        event = InputEvent(
            source=InputSource.CHAT,
            user_id=user_id,
            user_name=username,
            text=text,
        )
        return self.dispatcher.handle_input(event)
    
    def handle_asr_text(self, audio_text: str, user_id: str = "mic", username: str = "麦克风输入") -> OutputEvent:
        event = self.asr_listener.transcribe_to_event(
            audio_text=audio_text,
            user_id=user_id,
            username=username,
        )
        return self.dispatcher.handle_input(event)
    
    def get_speaking_state(self) -> SpeakingState:
        return self.speaking_state