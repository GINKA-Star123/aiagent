from aiagent.brain.agent_core import AgentCore
from aiagent.brain.dialogue_manager import DialogueManager
from aiagent.expression.output_broadcaster import OutputBroadcaster
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.interrupt_manager import InterruptManager
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.persona.persona_manager import PersonaManager
from aiagent.schemas.events import SystemEvent, SystemEventType
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import OutputEvent
from aiagent.state.agent_state import AgentRuntimeState
from aiagent.state.conversation_state import ConversationState
from aiagent.state.redis_state_store import RedisStateStore

class EventDispatcher:
    def __init__(
        self,
        event_bus: EventBus,
        scheduler: Scheduler,
        session_manager: SessionManager,
        agent_core: AgentCore,
        persona_manager: PersonaManager,
        output_broadcaster: OutputBroadcaster,
        agent_state: AgentRuntimeState,
        conversation_state: ConversationState,
        dialogue_manager: DialogueManager,
        interrupt_manager: InterruptManager,
        shared_state_store: RedisStateStore | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.session_manager = session_manager
        self.agent_core = agent_core
        self.persona_manager = persona_manager
        self.output_broadcaster = output_broadcaster
        self.agent_state = agent_state
        self.conversation_state = conversation_state
        self.dialogue_manager = dialogue_manager
        self.interrupt_manager = interrupt_manager
        self.shared_state_store = shared_state_store

    def _handle_input_unlocked(self, event: InputEvent) -> OutputEvent:
        session_id = self.session_manager.resolve_session_id(event)
        turn_id = self.session_manager.resolve_turn_id(event,session_id=session_id)

        event.session_id = session_id
        event.turn_id = turn_id

        self.agent_state.current_session_id = session_id
        self.agent_state.current_turn_id = turn_id

        accepted, reason = self.dialogue_manager.should_accept(event)
        if not accepted:
            raise ValueError(reason)

        interrupt_reason = self.interrupt_manager.consume_interrupt()
        if interrupt_reason:
            self.event_bus.publish(
                SystemEvent(
                    event_type=SystemEventType.ERROR,
                    payload={"interrupt_reason": interrupt_reason},
                )
            )

        self.conversation_state.add_input(event)

        self.event_bus.publish(
            SystemEvent(
                event_type=SystemEventType.INPUT_RECEIVED,
                payload={"event_id": event.event_id, "text": event.text},
            )
        )

        if not self.scheduler.should_process_now(event):
            raise ValueError("Empty input event cannot be processed.")

        persona = self.persona_manager.get_active_persona()
        packet = self.agent_core.main_runner.run(
            event=event,
            persona_runtime=persona,
            history=self.agent_core._build_history_lines(session_id=session_id),
            session_id=session_id,
            turn_id=turn_id,
        )
        output = OutputEvent(packet=packet)

        output = self.output_broadcaster.broadcast(output)

        self.agent_state.last_output_id = output.output_id
        self.conversation_state.add_output(output)
        self.dialogue_manager.record_turn(session_id=session_id, event=event, output=output)

        self.event_bus.publish(
            SystemEvent(
                event_type=SystemEventType.RESPONSE_READY,
                payload={
                    "output_id": output.output_id,
                    "reply_text": output.packet.reply_text,
                    "base_reply_text": output.packet.base_reply_text or "",
                    "audio_path": output.packet.audio_path or "",
                },
            )
        )

        return output

    def handle_input(
        self,
        event: InputEvent,
    ) -> OutputEvent:
        session_id = self.session_manager.resolve_session_id(event)
        event.session_id = session_id

        if self.shared_state_store is None:
            return self._handle_input_unlocked(event)

        with self.shared_state_store.session_lock(
            session_id=session_id,
            lease_seconds=60,
        ):
            return self._handle_input_unlocked(event)