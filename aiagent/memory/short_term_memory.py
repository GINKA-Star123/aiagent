from collections import deque

from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import OutputEvent


class ShortTermMemory:
    def __init__(self, max_turns: int = 12) -> None:
        self.max_turns = max_turns
        self.inputs: deque[InputEvent] = deque(maxlen=max_turns)
        self.outputs: deque[OutputEvent] = deque(maxlen=max_turns)

    def add_input(self, event: InputEvent) -> None:
        self.inputs.append(event)

    def add_output(self, event: OutputEvent) -> None:
        self.outputs.append(event)

    def recent_dialogue_lines(self, limit: int = 6) -> list[str]:
        lines: list[str] = []

        recent_inputs = list(self.inputs)[-limit:]
        recent_outputs = list(self.outputs)[-limit:]

        for item in recent_inputs:
            lines.append(f"观众 {item.user_name}: {item.text}")

        for item in recent_outputs:
            lines.append(f"主播: {item.packet.reply_text}")

        return lines[-limit:]
