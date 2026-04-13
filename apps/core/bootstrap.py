"""Bootstrap helpers for assembling the runtime container."""
import logging

from aiagent.brain.agent_core import AgentCore
from aiagent.brain.context_builder import ContextBuilder
from aiagent.brain.response_planner import ResponsePlanner
from aiagent.brain.safety_guard import SafetyGuard
from aiagent.orchestrator.dispatcher import EventDispatcher
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.schemas.persona import PersonaConfig
from aiagent.services.llm_service import LLMService
from aiagent.state.agent_state import AgentRuntimeState
from aiagent.state.conversation_state import ConversationState
from aiagent.state.emotion_state import EmotionState
from apps.core.runtime import CoreRuntime
from config.settings import settings


def build_runtime() -> CoreRuntime:
    logging.basicConfig(level=settings.log_level)

    persona = PersonaConfig(
        name=settings.persona_name,
        description=settings.persona_description,
        style=settings.persona_style,
        rules=settings.persona_rules,
    )

    agent_state = AgentRuntimeState()
    conversation_state = ConversationState()
    emotion_state = EmotionState()

    llm_service = LLMService(settings)
    context_builder = ContextBuilder()
    response_planner = ResponsePlanner()
    safety_guard = SafetyGuard()

    agent_core = AgentCore(
        llm_service=llm_service,
        context_builder=context_builder,
        response_planner=response_planner,
        safety_guard=safety_guard,
        agent_state=agent_state,
        conversation_state=conversation_state,
        emotion_state=emotion_state,
    )

    event_bus = EventBus()
    scheduler = Scheduler()
    session_manager = SessionManager()

    dispatcher = EventDispatcher(
        event_bus=event_bus,
        scheduler=scheduler,
        session_manager=session_manager,
        agent_core=agent_core,
        persona=persona,
        agent_state=agent_state,
        conversation_state=conversation_state,
    )

    return CoreRuntime(dispatcher=dispatcher)
