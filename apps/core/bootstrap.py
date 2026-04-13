import logging

from aiagent.brain.agent_core import AgentCore
from aiagent.brain.context_builder import ContextBuilder
from aiagent.brain.response_planner import ResponsePlanner
from aiagent.brain.safety_guard import SafetyGuard
from aiagent.expression.output_broadcaster import OutputBroadcaster
from aiagent.expression.tts_dispatcher import TTSDispatcher
from aiagent.memory.memory_store import MemoryStore
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.memory.short_term_memory import ShortTermMemory
from aiagent.orchestrator.dispatcher import EventDispatcher
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.perception.asr_listener import ASRListener
from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_manager import PersonaManager
from aiagent.persona.style_rewriter import StyleRewriter
from aiagent.services.llm_service import LLMService
from aiagent.state.agent_state import AgentRuntimeState
from aiagent.state.conversation_state import ConversationState
from aiagent.state.emotion_state import EmotionState
from aiagent.state.speaking_state import SpeakingState
from apps.core.runtime import CoreRuntime
from config.settings import settings
from integrations.tts.mock_tts_client import MockTTSClient
from integrations.asr.mock_asr_client import MockASRClient


def build_runtime() -> CoreRuntime:
    logging.basicConfig(level=settings.log_level)

    agent_state = AgentRuntimeState()
    conversation_state = ConversationState()
    emotion_state = EmotionState()
    speaking_state = SpeakingState()

    short_term_memory = ShortTermMemory()
    user_profile_memory = UserProfileMemory()
    memory_store = MemoryStore()

    llm_service = LLMService(settings=settings)
    context_builder = ContextBuilder(
        short_term_memory=short_term_memory,
        user_profile_memory=user_profile_memory
    )
    response_planner = ResponsePlanner()
    safety_guard = SafetyGuard()

    persona_loader = PersonaLoader()
    persona_manager = PersonaManager(loader=persona_loader)
    style_rewriter = StyleRewriter(llm_service=llm_service)

    agent_core = AgentCore(
        llm_service=llm_service,
        context_builder=context_builder,
        response_planner=response_planner,
        safety_guard=safety_guard,
        style_rewriter=style_rewriter,
        agent_state=agent_state,
        conversation_state=conversation_state,
        emotion_state=emotion_state,
    )

    tts_client = MockTTSClient()
    tts_dispatcher = TTSDispatcher(
        tts_client=tts_client,
        speaking_state=speaking_state)
    output_broadcaster = OutputBroadcaster(tts_dispatcher=tts_dispatcher)

    asr_listener = ASRListener(asr_client=MockASRClient())

    event_bus = EventBus()
    scheduler = Scheduler()
    session_manager = SessionManager()

    dispatcher = EventDispatcher(
        event_bus=event_bus,
        scheduler=scheduler,
        session_manager=session_manager,
        agent_core=agent_core,
        persona_manager=persona_manager,
        output_broadcaster=output_broadcaster,
        memory_store=memory_store,
        user_profile_memory=user_profile_memory,
        short_term_memory=short_term_memory,
        agent_state=agent_state,
        conversation_state=conversation_state,
    )

    return CoreRuntime(
        dispatcher=dispatcher,
        speaking_state=speaking_state,
        asr_listener=asr_listener
        )
