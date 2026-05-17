from aiagent.brain.agent_core import AgentCore
from aiagent.brain.dialogue_manager import DialogueManager
from aiagent.cognition.planner_normalizer import PlannerNormalizer
from aiagent.cognition.planner_reply import ReplyPlanner
from aiagent.cognition.state_analyzer import StateAnalyzer
from aiagent.cognition.state_normalizer import StateNormalizer
from aiagent.common.logger import setup_logger
from aiagent.expression.audio_playback_dispatcher import AudioPlaybackDispatcher
from aiagent.expression.live2d_payload_dispatcher import Live2DDispatcher
from aiagent.expression.mock_live2d_dispatcher import NoopLive2DDispatcher
from aiagent.expression.motion_policy import MotionPolicy
from aiagent.expression.output_broadcaster import OutputBroadcaster
from aiagent.expression.tts_dispatcher import TTSDispatcher
from aiagent.graphs.llm_graph import LLMRunner
from aiagent.graphs.main_graph import MainRunner
from aiagent.graphs.memory_graph import MemoryRunner
from aiagent.graphs.planner_graph import PlannerRunner
from aiagent.graphs.rag_graph import RAGRunner
from aiagent.graphs.state_graph import StateRunner
from aiagent.graphs.vision_graph import VisionRunner
from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever
from aiagent.knowledge.vector_store import LangChainVectorStore
from aiagent.live2d.motion_mapper import Live2DMotionMapper
from aiagent.live2d.payload_builder import Live2DPayloadBuilder
from aiagent.live2d.registry import Live2DRegistry
from aiagent.live2d.scene_mapper import Live2DSceneMapper
from aiagent.vision.character_registry import CharacterRegistry
from aiagent.vision.character_retriever import CharacterRetriever
from aiagent.vision.image_store import ImageStore
from aiagent.memory.mem0_memory import Mem0LongTermMemory
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
from aiagent.services.vision_service import VisionService
from aiagent.services.memory_policy_llm_service import MemoryPolicyLLMService
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
from integrations.live2d.file_live2d_client import FileLive2DClient
from integrations.tts.gpt_sovits_client import GPTSoVITSClient
from integrations.tts.indextts2_client import IndexTTS2Client
from integrations.tts.mock_tts_client import MockTTSClient
from integrations.tts.voxcpm_client import VoxCPMClient


def _resolve_env_secret(value: str | None) -> str | None:
    if value is None:
        return None

    import os

    candidate = value.strip()
    if not candidate:
        return None

    env_value = os.getenv(candidate)
    if env_value:
        return env_value.strip()

    if candidate.lower().startswith(("sk-", "sk_", "api-", "pk-")):
        return candidate

    return None


def build_runtime() -> CoreRuntime:
    setup_logger(settings.log_level)

    agent_state = AgentRuntimeState()
    conversation_state = ConversationState()
    emotion_state = EmotionState()
    speaking_state = SpeakingState()
    streaming_state = StreamingState()

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
            device=settings.rag_embedding_device,
            local_files_only=settings.rag_embedding_local_files_only,
            embedding_provider=settings.rag_embedding_provider,
            embedding_api_key=_resolve_env_secret(settings.rag_embedding_api_key_env),
            embedding_base_url=(
                settings.rag_embedding_base_url
                or (
                    settings.siliconflow_base_url
                    if settings.rag_embedding_provider.strip().lower() == "siliconflow"
                    else None
                )
            ),
            embedding_batch_size=settings.rag_embedding_batch_size,
            embedding_dimensions=settings.rag_embedding_dimensions,
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
    if settings.vision_provider.strip().lower() == "lmstudio":
        vision_api_key = settings.lmstudio_api_key or "lm-studio"
    else:
        vision_api_key = _resolve_env_secret(settings.vision_api_key_env)

    vision_service = VisionService(
        image_store=ImageStore(
            upload_dir=settings.vision_upload_dir,
            max_bytes=settings.vision_max_image_bytes,
        ),
        character_retriever=CharacterRetriever(
            registry=CharacterRegistry(
                root_dir=settings.vision_character_root_dir,
            ),
            embedding_model_name=settings.vision_character_embedding_model_name,
            embedding_model_path=settings.vision_character_embedding_model_path,
            device=settings.vision_character_embedding_device,
            local_files_only=settings.vision_character_embedding_local_files_only,
            cache_dir=settings.vision_character_index_dir,
            confident_score=settings.vision_character_confident_score,
        ),
        provider=settings.vision_provider,
        model=settings.vision_model,
        api_key=vision_api_key,
        base_url=(
            settings.lmstudio_base_url
            if settings.vision_provider.strip().lower() == "lmstudio"
            else
            settings.vision_base_url
            or (
                settings.siliconflow_base_url
                if settings.vision_provider.strip().lower() == "siliconflow"
                else settings.openai_base_url
                if settings.vision_provider.strip().lower() == "openai"
                else ""
            )
        ),
        timeout_seconds=settings.vision_timeout_seconds,
        confident_score=settings.vision_character_confident_score,
    )
    vision_runnner = VisionRunner(vision_service=vision_service)

    state_llm_service = StateLLMService(settings=settings)
    state_runner = StateRunner(
        state_analyzer=StateAnalyzer(llm_service=state_llm_service),
        state_normalizer=StateNormalizer(),
    )

    planner_llm_service = PlannerLLMService(settings=settings)
    planner_runner = PlannerRunner(
        planner_reply=ReplyPlanner(llm_service=planner_llm_service),
        planner_normalizer=PlannerNormalizer(),
    )

    llm_service = LLMService(settings=settings)
    llm_runner = LLMRunner(llm_service=llm_service, short_term_turn_window=6)

    long_term_memory = Mem0LongTermMemory(
        llm_provider=settings.memory_llm_provider,
        llm_model=settings.memory_llm_model,
        llm_api_key_env=settings.memory_llm_api_key_env,
        embedder_provider=settings.memory_embedder_provider,
        embedder_model=settings.memory_embedder_model,
        embedder_api_key_env=settings.memory_embedder_api_key_env,
        embedder_base_url=(
            settings.siliconflow_base_url
            if settings.memory_embedder_provider.strip().lower() == "siliconflow"
            else None
        ),
        vector_provider=settings.memory_vector_provider,
        vector_collection=settings.memory_vector_collection,
        embedding_dims=settings.memory_embedding_dims,
        qdrant_host=settings.qdrant_host,
        qdrant_port=settings.qdrant_port,
        enable_graph=settings.memory_enable_graph,
        graph_provider=settings.memory_graph_provider,
        graph_url=settings.neo4j_url,
        graph_username=settings.neo4j_username,
        graph_password=settings.neo4j_password,
        graph_database=settings.neo4j_database,
        reset_vector_store=settings.memory_reset_vector_store,
    )

    memory_runner = MemoryRunner(
        memory=long_term_memory,
        policy_service=MemoryPolicyLLMService(llm_service=llm_service),
    )

    main_runner = MainRunner(
        state_runner=state_runner,
        planner_runner=planner_runner,
        llm_runner=llm_runner,
        rag_runner=rag_runner,
        memory_runner=memory_runner,
        vision_runner=vision_runnner,
    )

    persona_loader = PersonaLoader()
    persona_manager = PersonaManager(loader=persona_loader)

    agent_core = AgentCore(
        main_runner=main_runner,
        agent_state=agent_state,
        conversation_state=conversation_state,
        emotion_state=emotion_state,
    )

    tts_dispatcher = TTSDispatcher(
        mock_tts_client=MockTTSClient(),
        speaking_state=speaking_state,
        tts_provider=settings.tts_provider,
        enable_mock_tts=settings.enable_mock_tts,
        gpt_sovits_client=GPTSoVITSClient(
            base_url=settings.gpt_sovits_base_url,
            timeout_seconds=settings.tts_timeout_seconds,
            ref_audio_path=settings.gpt_sovits_ref_audio_path,
            prompt_text=settings.gpt_sovits_prompt_text,
            prompt_lang=settings.gpt_sovits_prompt_lang,
            text_lang=settings.gpt_sovits_text_lang,
        ),
        index_tts2_client=IndexTTS2Client(
            base_url=settings.indextts2_base_url,
            ref_audio_path=settings.indextts2_ref_audio_path,
            emo_alpha=settings.indextts2_emo_alpha,
            use_emo_text=settings.indextts2_use_emo_text,
            max_segment_length=settings.indextts2_max_segment_length,
            timeout_seconds=settings.tts_timeout_seconds,
        ),
        voxcpm_client=VoxCPMClient(
            base_url=settings.voxcpm_base_url,
            timeout_seconds=settings.tts_timeout_seconds,
        ),
    )

    audio_playback_dispatcher = AudioPlaybackDispatcher(
        audio_player=AudioPlayer(),
        speaking_state=speaking_state,
    )
    live2d_dispatcher = None

    if settings.live2d_provider.strip().lower() in {"mock", "noop", "disabled"}:
        live2d_dispatcher = NoopLive2DDispatcher()
    else:
        live2d_registry = Live2DRegistry(
            character_root="data/live2d/characters",
            background_root="data/live2d/backgrounds",
        )
        live2d_builder = Live2DPayloadBuilder(
            registry=live2d_registry,
            motion_mapper=Live2DMotionMapper(),
            scene_mapper=Live2DSceneMapper(),
        )
        live2d_dispatcher = Live2DDispatcher(
            client=FileLive2DClient(payload_builder=live2d_builder),
        )

    output_broadcaster = OutputBroadcaster(
        tts_dispatcher=tts_dispatcher, 
        live2d_dispatcher=live2d_dispatcher, # type: ignore
        motion_policy=MotionPolicy(),
        audio_playback_dispatcher=audio_playback_dispatcher,
        enable_local_audio_playback=settings.enable_local_audio_playback,
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

    asr_listener = ASRListener(
        asr_client=asr_client,
        recorder=MicrophoneRecorder(sample_rate=settings.asr_sample_rate, channels=1),
        asr_provider=settings.asr_provider,
        enable_mock_asr=settings.enable_mock_asr,
    )

    voice_session_controller = VoiceSessionController(
        audio_playback_dispatcher=audio_playback_dispatcher,
        speaking_state=speaking_state,
        streaming_state=streaming_state,
    )

    voice_turn_manager = VoiceTurnManager(
        asr_listener=asr_listener,
        microphone=StreamingMicrophone(
            sample_rate=settings.asr_sample_rate,
            channels=1,
            chunk_seconds=settings.voice_chunk_seconds,
            vad=VoiceActivityDetector(energy_threshold=settings.voice_energy_threshold),
        ),
        stream_state=streaming_state,
        session_controller=voice_session_controller,
    )

    source_router = SourceRouter(input_normalizer=InputNormalizer())

    dispatcher = EventDispatcher(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        session_manager=SessionManager(),
        agent_core=agent_core,
        persona_manager=persona_manager,
        output_broadcaster=output_broadcaster,
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
        memory_runner=memory_runner,
        source_router=source_router,
        llm_service=llm_service,
        conversation_state=conversation_state,
        dialogue_manager=dialogue_manager,
        interrupt_manager=interrupt_manager,
        rag_pipeline=rag_pipeline,
        voice_turn_manager=voice_turn_manager,
        voice_session_controller=voice_session_controller,
        vision_service=vision_service,
        vision_runner=vision_runnner,
    )
