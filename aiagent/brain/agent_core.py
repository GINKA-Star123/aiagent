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

    def process(self, event: InputEvent, persona: PersonaRuntime,session_id: str = "",) -> ResponsePacket:
        self.agent_state.status = AgentStatus.THINKING
        self.agent_state.last_input_id = event.event_id
        self.agent_state.error_message = None

        try:
            history = self._build_history_lines(session_id=session_id)

            packet = self.main_runner.run(
                event=event,
                persona_runtime=persona,
                history=history,
                session_id=session_id,
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

    def _build_history_lines(self, session_id: str) -> list[str]:
        runner = self.main_runner.llm_runner
        thread_id = session_id
        shared_history = runner.recent_dialogue_lines(thread_id=thread_id, limit=8)
        if shared_history:
            return shared_history

        # 仅在明确 local 模式下使用旧的进程内状态作为兼容回退。
        if getattr(runner, "shared_state_store", None) is not None:
            return []

        return [ # type: ignore
            pair
            for pair in self.conversation_state.recent_dialogue_pairs(
                limit=4,
                session_id=session_id,
            )
        ]
