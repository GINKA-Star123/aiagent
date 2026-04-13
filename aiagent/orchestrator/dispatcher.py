"""Dispatch incoming events to appropriate pipelines."""
from aiagent.brain.agent_core import AgentCore
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.schemas.events import SystemEvents,SystemEventType
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import OutputEvent
from aiagent.schemas.persona import PersonaConfig
from aiagent.state.agent_state import AgentRuntimeState
from aiagent.state.conversation_state import ConversationState

class EventDispatcher:
    def __init__(
            self,
            event_bus : EventBus,
            scheduler : Scheduler,
            session_manager : SessionManager,
            agent_core : AgentCore,
            persona: PersonaConfig,
            agent_state: AgentRuntimeState,
            conversation_state: ConversationState,
    ) ->None:
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.session_manager = session_manager
        self.agent_core = agent_core
        self.persona = persona
        self.agent_state = agent_state
        self.conversation_state = conversation_state
    
    def handle_input(self,event:InputEvent) -> OutputEvent:
        self.agent_state.current_session_id = self.session_manager.resolve_session_id(event)
        self.conversation_state.add_input(event)

        self.event_bus.publish(
            SystemEvents(
                event_type=SystemEventType.INPUT_RECEIVED,
                payload={
                    "event_id":event.event_id,
                    "text":event.text
                }
            )
        )
        
        if not self.scheduler.should_process_now(event):
            raise ValueError("Event is scheduled for later processing")
        
        packet = self.agent_core.process(event,self.persona)
        output = OutputEvent(packet=packet)


        self.agent_state.last_output_id = output.output_id
        self.conversation_state.add_output(output)

        self.event_bus.publish(
            SystemEvents(
                event_type=SystemEventType.RESPONSE_READY,
                payload={
                    "output_id":output.output_id,
                    "reply_text":packet.reply_text
                }
            )
        )

        return output