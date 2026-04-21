from aiagent.brain.agent_core import AgentCore
from aiagent.brain.dialogue_manager import DialogueManager
from aiagent.expression.output_broadcaster import OutputBroadcaster
from aiagent.memory.long_term_memory import LongTermMemory
from aiagent.memory.memory_selector import MemorySelector
from aiagent.memory.memory_store import MemoryStore
from aiagent.memory.memory_summarizer import MemorySummarizer
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.interrupt_manager import InterruptManager
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.persona.persona_manager import PersonaManager
from aiagent.schemas.events import SystemEvent, SystemEventType
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.memory import MemoryKind
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
        memory_store: MemoryStore,
        memory_selector: MemorySelector,
        memory_summarizer: MemorySummarizer,
        long_term_memory: LongTermMemory,
        user_profile_memory: UserProfileMemory,
        agent_state: AgentRuntimeState,
        conversation_state: ConversationState,
        dialogue_manager: DialogueManager,
        interrupt_manager: InterruptManager,
    ) -> None:
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.session_manager = session_manager
        self.agent_core = agent_core
        self.persona_manager = persona_manager
        self.output_broadcaster = output_broadcaster
        self.memory_store = memory_store
        self.memory_selector = memory_selector
        self.memory_summarizer = memory_summarizer
        self.long_term_memory = long_term_memory
        self.user_profile_memory = user_profile_memory
        self.agent_state = agent_state
        self.conversation_state = conversation_state
        self.dialogue_manager = dialogue_manager
        self.interrupt_manager = interrupt_manager

    def handle_input(self, event: InputEvent) -> OutputEvent:
        session_id = self.session_manager.resolve_session_id(event)
        self.agent_state.current_session_id = session_id

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
        packet = self.agent_core.process(event, persona)
        output = OutputEvent(packet=packet)

        output = self.output_broadcaster.broadcast(output)
        self._store_memories(event, output)

        self.agent_state.last_output_id = output.output_id
        self.conversation_state.add_output(output)
        self.dialogue_manager.record_turn(session_id=session_id, event=event, output=output)

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

    def _store_memories(self, event: InputEvent, output: OutputEvent) -> None:
        profile_items = self.memory_selector.extract_profile_memories(event)
        self.memory_store.store_profile_memories(
            user_profile_memory=self.user_profile_memory,
            items=profile_items,
        )

        long_term_items = self.memory_selector.extract_long_term_memories(event, output)
        stored_count = self.memory_store.store_long_term_memories(
            long_term_memory=self.long_term_memory,
            items=long_term_items,
        )

        if stored_count > 0:
            summary_source_items = self.long_term_memory.recall_for_user(
                user_id=event.user_id,
                limit=12,
                kinds=[MemoryKind.USER_PORFILE, MemoryKind.LONG_TERM],
            )
            summary_text = self.memory_summarizer.summarize_user_memories(summary_source_items)
            self.long_term_memory.replace_user_summary(
                user_id=event.user_id,
                username=event.user_name,
                summary_text=summary_text,
            )
