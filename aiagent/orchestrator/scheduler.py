"""Schedule response generation and output work."""
from aiagent.schemas.inputs import InputEvent

class Scheduler:
    def should_process_now(self,event:InputEvent) ->bool:
        return bool(event.text.strip())