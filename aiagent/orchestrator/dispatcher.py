from aiagent.brain.agent_core import AgentCore
from aiagent.expression.output_broadcaster import OutputBroadcaster
from aiagent.memory.memory_store import MemoryStore
from aiagent.memory.short_term_memory import ShortTermMemory
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.persona.persona_manager import PersonaManager
from aiagent.schemas.events import SystemEvent, SystemEventType
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import OutputEvent
from aiagent.state.agent_state import AgentRuntimeState
from aiagent.state.conversation_state import ConversationState


class EventDispatcher:
    def __init__(
        self,
        event_bus: EventBus,
        scheduler: Scheduler,
        session_manager: SessionManager,
        agent_core: AgentCore,
        persona_manager: PersonaManager,
        output_broadcaster: OutputBroadcaster,
        memory_store:MemoryStore,
        short_term_memory: ShortTermMemory,
        user_profile_memory: UserProfileMemory,
        agent_state: AgentRuntimeState,
        conversation_state: ConversationState,
    ) -> None:
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.session_manager = session_manager
        self.agent_core = agent_core
        self.persona_manager = persona_manager
        self.output_broadcaster = output_broadcaster
        self.memory_store = memory_store
        self.short_term_memory = short_term_memory
        self.user_profile_memory = user_profile_memory
        self.agent_state = agent_state
        self.conversation_state = conversation_state

    def handle_input(self, event: InputEvent) -> OutputEvent:
        self.agent_state.current_session_id = self.session_manager.resolve_session_id(event)
        self.conversation_state.add_input(event)
        self.short_term_memory.add_input(event)

        self.event_bus.publish(
            SystemEvent(
                event_type=SystemEventType.INPUT_RECEIVED,
                payload={"event_id": event.event_id, "text": event.text},
            )
        )

        if not self.scheduler.should_process_now(event):
            raise ValueError("Empty input event cannot be processed.")

        persona = self.persona_manager.get_active_persona()
        packet = self.agent_core.process(event, persona)
        output = OutputEvent(packet=packet)

        output = self.output_broadcaster.broadcast(output)

        self.agent_state.last_output_id = output.output_id
        self.conversation_state.add_output(output)
        self.short_term_memory.add_output(output)

        self.event_bus.publish(
            SystemEvent(
                event_type=SystemEventType.RESPONSE_READY,
                payload={
                    "output_id": output.output_id,
                    "reply_text": packet.reply_text,
                    "base_reply_text": packet.base_reply_text or "",
                    "audio_path": packet.audio_path or "",
                },
            )
        )

        return output
