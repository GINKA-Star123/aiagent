"""Runtime lifecycle management for the core application."""
from aiagent.orchestrator.dispatcher import EventDispatcher
from aiagent.schemas.inputs import InputEvent, InputSource

class CoreRuntime:
    def __init__(self, dispatcher: EventDispatcher) -> None:
        self.dispatcher = dispatcher

    def handle_chat(self,text:str,user_id : str="guest",username:str ="guest") ->str:
        event = InputEvent(
            source=InputSource.CHAT,
            text=text,
            user_id=user_id,
            user_name=username,
        )
        output = self.dispatcher.handle_input(event)
        return output.packet.reply_text