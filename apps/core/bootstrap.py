from aiagent.brain.agent_core import AgentCore
from aiagent.brain.dialogue_manager import DialogueManager
from aiagent.cognition.planner_normalizer import PlannerNormalizer
from aiagent.cognition.planner_reply import ReplyPlanner
from aiagent.cognition.state_analyzer import StateAnalyzer
from aiagent.cognition.state_normalizer import StateNormalizer
from aiagent.common.logger import setup_logger
from aiagent.expression.audio_playback_dispatcher import AudioPlaybackDispatcher
from aiagent.expression.live2d_dispatcher import Live2DDispatcher
from aiagent.expression.motion_policy import MotionPolicy
from aiagent.expression.output_broadcaster import OutputBroadcaster
from aiagent.expression.tts_dispatcher import TTSDispatcher
from aiagent.graphs.llm_graph import LLMRunner
from aiagent.graphs.main_graph import MainRunner
from aiagent.graphs.planner_graph import PlannerRunner
from aiagent.graphs.state_graph import StateRunner
from aiagent.graphs.rag_graph import RAGRunner
from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever
from aiagent.knowledge.vector_store import LangChainVectorStore
from aiagent.memory.long_term_memory import LongTermMemory
from aiagent.memory.memory_selector import MemorySelector
from aiagent.memory.memory_store import MemoryStore
from aiagent.memory.memory_summarizer import MemorySummarizer
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.orchestrator.dispatcher import EventDispatcher
from aiagent.orchestrator.event_bus import EventBus
from aiagent.orchestrator.interrupt_manager import InterruptManager
from aiagent.orchestrator.scheduler import Scheduler
from aiagent.orchestrator.session_manager import SessionManager
from aiagent.perception.asr_listener import ASRListener
from aiagent.perception.input_normalizer import InputNormalizer
from aiagent.perception.source_router import SourceRouter
from aiagent.perception.voice_session_controller import VoiceSessionController
from aiagent.perception.voice_turn_manager import VoiceTurnManager
from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_manager import PersonaManager
from aiagent.services.llm_service import LLMService
from aiagent.services.planner_llm_service import PlannerLLMService
from aiagent.services.state_llm_service import StateLLMService
from aiagent.state.agent_state import AgentRuntimeState
from aiagent.state.conversation_state import ConversationState
from aiagent.state.emotion_state import EmotionState
from aiagent.state.speaking_state import SpeakingState
from aiagent.state.stream_state import StreamingState
from apps.core.runtime import CoreRuntime
from config.settings import settings
from integrations.asr.faster_whisper_client import FasterWhisperClient
from integrations.asr.microphone import StreamingMicrophone
from integrations.asr.mock_asr_client import MockASRClient
from integrations.asr.vad import VoiceActivityDetector
from integrations.audio.audio_player import AudioPlayer
from integrations.audio.microphone_recorder import MicrophoneRecorder
from integrations.live2d.mock_live2d_client import MockLive2DClient
from integrations.tts.gpt_sovits_client import GPTSoVITSClient
from integrations.tts.indextts2_client import IndexTTS2Client
from integrations.tts.mock_tts_client import MockTTSClient
from integrations.tts.voxcpm_client import VoxCPMClient


def build_runtime() -> CoreRuntime:
    setup_logger(settings.log_level)

    agent_state = AgentRuntimeState()
    conversation_state = ConversationState()
    emotion_state = EmotionState()
    speaking_state = SpeakingState()
    streaming_state = StreamingState()

    user_profile_memory = UserProfileMemory()
    long_term_memory = LongTermMemory()
    memory_store = MemoryStore()
    memory_selector = MemorySelector()
    memory_summarizer = MemorySummarizer()

    dialogue_manager = DialogueManager()
    interrupt_manager = InterruptManager()

    rag_pipeline = RAGPipeline(
        loader=DocumentLoader(),
        retriever=HybridRetriever(
            bm25_top_k=settings.rag_bm25_top_k,
            vector_top_k=settings.rag_vector_top_k,
        ),
        vector_store=LangChainVectorStore(
            embedding_model_name=settings.rag_embedding_model_name,
            embedding_model_path=settings.rag_embedding_model_path,
        ),
        reranker=SimpleReranker(),
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        final_top_k=settings.rag_final_top_k,
    )
    rag_pipeline.build_index(force_rebuild=False)
    
    rag_runner = RAGRunner(
    rag_pipeline=rag_pipeline,
    top_k=settings.rag_final_top_k,
    min_cosine_score=0.42,
    require_relevance=True,
)

    state_llm_service = StateLLMService(settings=settings)
    state_analyzer = StateAnalyzer(llm_service=state_llm_service)
    state_normalizer = StateNormalizer()
    state_runner = StateRunner(
        state_analyzer=state_analyzer,
        state_normalizer=state_normalizer,
    )

    planner_llm_service = PlannerLLMService(settings=settings)
    planner_reply = ReplyPlanner(llm_service=planner_llm_service)
    planner_normalizer = PlannerNormalizer()
    planner_runner = PlannerRunner(
        planner_reply=planner_reply,
        planner_normalizer=planner_normalizer,
    )

    llm_service = LLMService(settings=settings)
    llm_runner = LLMRunner(
        llm_service=llm_service,
        short_term_turn_window=6,
    )

    main_runner = MainRunner(
        state_runner=state_runner,
        planner_runner=planner_runner,
        llm_runner=llm_runner,
        rag_runner=rag_runner,
    )

    persona_loader = PersonaLoader()
    persona_manager = PersonaManager(loader=persona_loader)

    agent_core = AgentCore(
        main_runner=main_runner,
        agent_state=agent_state,
        conversation_state=conversation_state,
        emotion_state=emotion_state,
    )

    mock_tts_client = MockTTSClient()

    gpt_sovits_client = GPTSoVITSClient(
        base_url=settings.gpt_sovits_base_url,
        timeout_seconds=settings.tts_timeout_seconds,
        ref_audio_path=settings.gpt_sovits_ref_audio_path,
        prompt_text=settings.gpt_sovits_prompt_text,
        prompt_lang=settings.gpt_sovits_prompt_lang,
        text_lang=settings.gpt_sovits_text_lang,
    )

    index_tts2_client = IndexTTS2Client(
        base_url=settings.indextts2_base_url,
        ref_audio_path=settings.indextts2_ref_audio_path,
        emo_alpha=settings.indextts2_emo_alpha,
        use_emo_text=settings.indextts2_use_emo_text,
        max_segment_length=settings.indextts2_max_segment_length,
        timeout_seconds=settings.tts_timeout_seconds,
    )

    voxcpm_client = VoxCPMClient(
        base_url=settings.voxcpm_base_url,
        timeout_seconds=settings.tts_timeout_seconds,
    )

    tts_dispatcher = TTSDispatcher(
        mock_tts_client=mock_tts_client,
        speaking_state=speaking_state,
        tts_provider=settings.tts_provider,
        enable_mock_tts=settings.enable_mock_tts,
        gpt_sovits_client=gpt_sovits_client,
        index_tts2_client=index_tts2_client,
        voxcpm_client=voxcpm_client,
    )

    audio_playback_dispatcher = AudioPlaybackDispatcher(
        audio_player=AudioPlayer(),
        speaking_state=speaking_state,
    )

    live2d_dispatcher = Live2DDispatcher(client=MockLive2DClient())
    motion_policy = MotionPolicy()

    output_broadcaster = OutputBroadcaster(
        tts_dispatcher=tts_dispatcher,
        live2d_dispatcher=live2d_dispatcher,
        motion_policy=motion_policy,
        audio_playback_dispatcher=audio_playback_dispatcher,
    )

    if settings.enable_mock_asr or settings.asr_provider == "mock":
        asr_client = MockASRClient()
    else:
        asr_client = FasterWhisperClient(
            model_size=settings.asr_model_size,
            model_path=settings.asr_model_path,
            device=settings.asr_device,
            compute_type=settings.asr_compute_type,
            language=settings.asr_language,
        )

    fixed_recorder = MicrophoneRecorder(
        sample_rate=settings.asr_sample_rate,
        channels=1,
    )

    asr_listener = ASRListener(
        asr_client=asr_client,
        recorder=fixed_recorder,
        asr_provider=settings.asr_provider,
        enable_mock_asr=settings.enable_mock_asr,
    )

    vad = VoiceActivityDetector(
        energy_threshold=settings.voice_energy_threshold,
    )
    streaming_microphone = StreamingMicrophone(
        sample_rate=settings.asr_sample_rate,
        channels=1,
        chunk_seconds=settings.voice_chunk_seconds,
        vad=vad,
    )

    voice_session_controller = VoiceSessionController(
        audio_playback_dispatcher=audio_playback_dispatcher,
        speaking_state=speaking_state,
        streaming_state=streaming_state,
    )

    voice_turn_manager = VoiceTurnManager(
        asr_listener=asr_listener,
        microphone=streaming_microphone,
        stream_state=streaming_state,
        session_controller=voice_session_controller,
    )

    input_normalizer = InputNormalizer()
    source_router = SourceRouter(input_normalizer=input_normalizer)

    dispatcher = EventDispatcher(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        session_manager=SessionManager(),
        agent_core=agent_core,
        persona_manager=persona_manager,
        output_broadcaster=output_broadcaster,
        memory_store=memory_store,
        memory_selector=memory_selector,
        memory_summarizer=memory_summarizer,
        long_term_memory=long_term_memory,
        user_profile_memory=user_profile_memory,
        agent_state=agent_state,
        conversation_state=conversation_state,
        dialogue_manager=dialogue_manager,
        interrupt_manager=interrupt_manager,
    )

    return CoreRuntime(
        dispatcher=dispatcher,
        agent_core=agent_core,
        speaking_state=speaking_state,
        asr_listener=asr_listener,
        stream_state=streaming_state,
        long_term_memory=long_term_memory,
        user_profile_memory=user_profile_memory,
        source_router=source_router,
        llm_service=llm_service,
        conversation_state=conversation_state,
        dialogue_manager=dialogue_manager,
        interrupt_manager=interrupt_manager,
        rag_pipeline=rag_pipeline,
        voice_turn_manager=voice_turn_manager,
        voice_session_controller=voice_session_controller,
    )
