from __future__ import annotations

from aiagent.graphs.main_graph import MainRunner
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import ResponsePacket
from aiagent.state.agent_state import AgentRuntimeState, AgentStatus
from aiagent.state.conversation_state import ConversationState
from aiagent.state.emotion_state import EmotionState


class AgentCore:
    def __init__(
        self,
        main_runner: MainRunner,
        agent_state: AgentRuntimeState,
        conversation_state: ConversationState,
        emotion_state: EmotionState,
    ) -> None:
        self.main_runner = main_runner
        self.agent_state = agent_state
        self.conversation_state = conversation_state
        self.emotion_state = emotion_state

    def process(self, event: InputEvent, persona: PersonaRuntime) -> ResponsePacket:
        self.agent_state.status = AgentStatus.THINKING
        self.agent_state.last_input_id = event.event_id
        self.agent_state.error_message = None

        try:
            history = self._build_history_lines()

            packet = self.main_runner.run(
                event=event,
                persona_runtime=persona,
                history=history,
            )

            self.emotion_state.current_emotion = packet.emotion
            self.agent_state.status = AgentStatus.IDLE
            return packet

        except Exception as exc:
            self.agent_state.status = AgentStatus.ERROR
            self.agent_state.error_message = str(exc)
            raise

    def clear_runtime_context(self) -> None:
        self.main_runner.clear_all_threads()

    def _build_history_lines(self) -> list[str]:
        lines: list[str] = []

        for pair in self.conversation_state.recent_dialogue_pairs(limit=4):
            user = str(pair.get("user", "")).strip()
            user_text = str(pair.get("input", "")).strip()
            reply_text = str(pair.get("reply", "")).strip()

            if user_text:
                lines.append(f"{user or '用户'}: {user_text}")
            if reply_text:
                lines.append(f"助手: {reply_text}")

        return lines
