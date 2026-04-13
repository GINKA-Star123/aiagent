"""Broadcast output events to external consumers."""
from aiagent.expression.tts_dispatcher import TTSDispatcher
from aiagent.schemas.outputs import OutputEvent

class OutputBroadcaster:

    def __init__(self,tts_dispatcher: TTSDispatcher) ->None:
        self.tts_dispatcher = tts_dispatcher

    def broadcast(self,output_event: OutputEvent) -> OutputEvent:

        output_event.packet = self.tts_dispatcher.dispatch(output_event.packet)
        return output_event