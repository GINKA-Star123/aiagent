import logging

from apps.core.capabilities import CapabilityRegistry

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
from aiagent.knowledge.null_rag_pipeline import NullRAGPipeline
from aiagent.live2d.motion_mapper import Live2DMotionMapper
from aiagent.live2d.payload_builder import Live2DPayloadBuilder
from aiagent.live2d.registry import Live2DRegistry
from aiagent.live2d.scene_mapper import Live2DSceneMapper
from aiagent.vision.character_registry import CharacterRegistry
from aiagent.vision.character_retriever import CharacterRetriever
from aiagent.vision.image_store import ImageStore
from aiagent.memory.mem0_memory import Mem0LongTermMemory
from aiagent.memory.null_memory import NullLongTermMemory
from aiagent.memory.memory_preferences import MemoryPreferenceStore
from aiagent.memory.memory_prompt import MemoryPromptBuilder
from aiagent.memory.memory_write_audit import MemoryWriteAuditLog
from aiagent.memory.memory_write_dispatcher import MemoryWriteDispatcher
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
from aiagent.state.redis_state_store import RedisStateStore
from aiagent.state.shared_state import SharedStateUnavailableError
from apps.core.runtime import CoreRuntime
from config.settings import settings
from cloud.config import cloud_settings
from integrations.asr.api_asr_client import ApiASRClient
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

logger = logging.getLogger("aiagent.runtime.bootstrap")


def _resolve_env_secret(value: str | None) -> str | None:
    """解析环境变量名，或兼容少量直接传入的密钥值。"""
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

def build_shared_state_store():
    mode = cloud_settings.execution_state_mode
    if mode == "local":
        return None

    if mode != "redis":
        raise RuntimeError(f"unsupported execution state mode: {mode}")

    if not cloud_settings.redis_url:
        if cloud_settings.execution_state_fail_closed:
            raise RuntimeError("redis execution state is required but REDIS_URL is empty")
        return None

    return RedisStateStore(
        redis_url=cloud_settings.redis_url,
        prefix=cloud_settings.redis_prefix,
        session_ttl_seconds=cloud_settings.execution_state_session_ttl_seconds,
        thread_ttl_seconds=cloud_settings.execution_state_thread_ttl_seconds,
        fail_closed=cloud_settings.execution_state_fail_closed,
    )

def build_llm_checkpointer():
    if cloud_settings.execution_state_mode == "local":
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()

    if cloud_settings.execution_state_mode != "redis":
        raise RuntimeError(
            "unsupported execution state mode: "
            f"{cloud_settings.execution_state_mode}"
        )

    if not cloud_settings.redis_url:
        raise RuntimeError(
            "REDIS_URL is required when EXECUTION_STATE_MODE=redis"
        )

    try:
        from langgraph.checkpoint.redis import RedisSaver
    except ImportError as exc:
        raise RuntimeError(
            "RedisSaver is not installed. "
            "Install langgraph-checkpoint-redis first."
        ) from exc

    try:
        checkpointer = RedisSaver(
            redis_url=cloud_settings.redis_url,
            checkpoint_prefix=f"{cloud_settings.redis_prefix}:checkpoint",
            checkpoint_write_prefix=f"{cloud_settings.redis_prefix}:checkpoint-write",
        )
        checkpointer.setup()
        return checkpointer
    except Exception as exc:
        raise SharedStateUnavailableError(
            "RedisSaver initialization failed; refusing to fall back to "
            "InMemorySaver in redis execution mode."
        ) from exc

def build_runtime() -> CoreRuntime:
    """根据配置组装后端长生命周期 runtime。"""
    setup_logger(settings.log_level)

    capabilities = CapabilityRegistry()

    capabilities.mark_initializing(
        "runtime",
        "Runtime build started.",
    )

    # 这些状态对象只创建一次，让图节点、API 路由、音频播放和控制动作
    # 看到同一个运行时会话。
    agent_state = AgentRuntimeState()
    conversation_state = ConversationState()
    emotion_state = EmotionState()
    speaking_state = SpeakingState()
    streaming_state = StreamingState()

    dialogue_manager = DialogueManager()
    interrupt_manager = InterruptManager()

    capabilities.mark_available(
        "runtime_state",
        "Runtime shared state objects are available.",
    )
    capabilities.mark_available(
        "dialogue_control",
        "Dialogue and interrupt managers are available.",
    )

    # RAG 正常启动时优先加载缓存索引；需要强制重建时走 /knowledge/rebuild。
    try:
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
            manifest_path=settings.rag_index_manifest_path or None,
            auto_rebuild_on_stale=settings.rag_auto_rebuild_on_stale,
        )
        rag_pipeline.build_index(force_rebuild=False)
        capabilities.mark_available(
            "rag",
            "RAG pipeline is available.",
            details={
                "embedding_provider": settings.rag_embedding_provider,
                "embedding_model": settings.rag_embedding_model_name,
            },
        )
    except Exception as exc:
        logger.exception("RAG pipeline init failed: %s", exc)
        rag_pipeline = NullRAGPipeline(reason=str(exc))
        capabilities.mark_degraded(
            "rag",
            "RAG pipeline failed to initialize. Text chat will continue without external knowledge.",
            details={
                "embedding_provider": settings.rag_embedding_provider,
                "embedding_model": settings.rag_embedding_model_name,
            },
            error=exc,
        )

    rag_runner = RAGRunner(
        rag_pipeline=rag_pipeline,
        top_k=settings.rag_final_top_k,
        min_cosine_score=0.42,
        require_relevance=True,
    )
    # Vision 分成通用图片理解和本地角色检索两部分。CharacterRetriever 会
    # 延迟加载 CLIP 模型，避免文本聊天启动时提前导入重型 ML 依赖。
    vision_service = None
    vision_runner = None
    vision_provider = settings.vision_provider.strip().lower()

    try:
        if vision_provider in {"disabled", "none"}:
            capabilities.mark_disabled(
                "vision",
                "Vision provider is disabled by config.",
                details={"provider": settings.vision_provider},
            )
        else:
            if vision_provider == "lmstudio":
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
                    if vision_provider == "lmstudio"
                    else
                    settings.vision_base_url
                    or (
                        settings.siliconflow_base_url
                        if vision_provider == "siliconflow"
                        else settings.openai_base_url
                        if vision_provider == "openai"
                        else ""
                    )
                ),
                timeout_seconds=settings.vision_timeout_seconds,
                confident_score=settings.vision_character_confident_score,
            )
            vision_runner = VisionRunner(vision_service=vision_service)
            capabilities.mark_available(
                "vision",
                "Vision service is available.",
                details={
                    "provider": settings.vision_provider,
                    "model": settings.vision_model,
                    "character_root": settings.vision_character_root_dir,
                },
            )
    except Exception as exc:
        logger.exception("Vision service init failed: %s", exc)
        capabilities.mark_degraded(
            "vision",
            "Vision service failed to initialize. Text chat will continue without image understanding.",
            details={
                "provider": settings.vision_provider,
                "model": settings.vision_model,
            },
            error=exc,
        )

    state_llm_service = StateLLMService(settings=settings)
    state_runner = StateRunner(
        state_analyzer=StateAnalyzer(llm_service=state_llm_service),
        state_normalizer=StateNormalizer(),
    )
    capabilities.mark_available(
        "state_llm",
        "State LLM service is configured.",
        details={
            "provider": settings.state_provider,
            "model": settings.state_model,
            "mock": settings.enable_mock_state,
        },
    )

    planner_llm_service = PlannerLLMService(settings=settings)
    planner_runner = PlannerRunner(
        planner_reply=ReplyPlanner(llm_service=planner_llm_service),
        planner_normalizer=PlannerNormalizer(),
    )
    capabilities.mark_available(
        "planner_llm",
        "Planner LLM service is configured.",
        details={
            "provider": settings.planner_provider,
            "model": settings.planner_model,
            "mock": settings.enable_mock_planner,
        },
    )

    shared_state_store = build_shared_state_store()

    llm_service = LLMService(settings=settings)
    llm_runner = LLMRunner(
        llm_service=llm_service,
        short_term_turn_window=6,
        shared_state_store=shared_state_store,
        checkpointer=build_llm_checkpointer(),
    )
    capabilities.mark_available(
        "llm",
        "Main LLM service is configured.",
        details={
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "mock": settings.enable_mock_llm,
        },
    )

    # MemoryRunner 每轮会使用两次：回复前检索长期记忆，回复后按策略写入。
    try:
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
        capabilities.mark_available(
            "memory",
            "Profile memory is available: identity/relationship memories are readable via /memory API.",
            details={
                "vector_provider": settings.memory_vector_provider,
                "collection": settings.memory_vector_collection,
                "graph_enabled": settings.memory_enable_graph,
                "layers": ["profile", "preference", "episode", "boundary", "other"],
                "search_scope": ["profile", "long_term"],
            },
        )
    except Exception as exc:
        logger.exception("Long-term memory init failed: %s", exc)
        long_term_memory = NullLongTermMemory(reason=str(exc))
        capabilities.mark_degraded(
            "memory",
            "Long-term memory failed to initialize. Chat will continue without persistent memory.",
            details={
                "vector_provider": settings.memory_vector_provider,
                "collection": settings.memory_vector_collection,
                "graph_enabled": settings.memory_enable_graph,
            },
            error=exc,
        )
    memory_preferences = MemoryPreferenceStore(
        path=settings.memory_preferences_path,
        default_long_term_enabled=settings.memory_long_term_default_enabled,
    )

    memory_prompt_builder = MemoryPromptBuilder(
        max_chars=settings.memory_prompt_max_chars,
        pinned_limit=settings.memory_prompt_pinned_limit,
        relevant_limit=settings.memory_prompt_relevant_limit,
        item_max_chars=settings.memory_prompt_item_max_chars,
    )

    memory_write_dispatcher = MemoryWriteDispatcher(
        max_pending=settings.memory_write_max_pending,
    )

    memory_write_audit = MemoryWriteAuditLog(
        tail_limit=settings.memory_write_audit_tail_limit,
    )
    
    memory_runner = MemoryRunner(
        memory=long_term_memory, # MemoryRunner 每轮会使用两次：回复前检索长期记忆，回复后按策略写入。 # type: ignore
        policy_service=MemoryPolicyLLMService(llm_service=llm_service),
        preference_store=memory_preferences,
        prompt_builder=memory_prompt_builder,
        write_dispatcher=memory_write_dispatcher,
        audit_log=memory_write_audit,
        async_write_enabled=settings.memory_write_async_enabled,
    )

    main_runner = MainRunner(
        state_runner=state_runner,
        planner_runner=planner_runner,
        llm_runner=llm_runner,
        rag_runner=rag_runner,
        memory_runner=memory_runner,
        vision_runner=vision_runner,
    )

    persona_loader = PersonaLoader()

    persona_manager = PersonaManager(
        loader=persona_loader,
        shared_state_store=shared_state_store,
    )
    
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
    if settings.enable_mock_tts or settings.tts_provider.strip().lower() == "mock":
        capabilities.mark_degraded(
            "tts",
            "TTS uses mock provider.",
            details={
                "provider": settings.tts_provider,
                "mock": True,
            },
        )
    else:
        capabilities.mark_available(
            "tts",
            "TTS dispatcher is configured.",
            details={
                "provider": settings.tts_provider,
                "timeout_seconds": settings.tts_timeout_seconds,
            },
        )

    audio_playback_dispatcher = AudioPlaybackDispatcher(
        audio_player=AudioPlayer(),
        speaking_state=speaking_state,
    )
    live2d_dispatcher = None

    # 后端 Live2D 可以先 mock；手机端有内置过渡模型。provider 非 mock/noop
    # 时才启用真实文件 payload。
    if settings.live2d_provider.strip().lower() in {"mock", "noop", "disabled"}:
        live2d_dispatcher = NoopLive2DDispatcher()
        capabilities.mark_disabled(
            "live2d_output",
            "Live2D backend dispatch uses noop provider.",
            details={
                "provider": settings.live2d_provider,
                "enable_live2d_runtime": settings.enable_live2d_runtime,
            },
        )
    else:
        try:
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
            capabilities.mark_available(
                "live2d_output",
                "Live2D backend dispatch is configured.",
                details={
                    "provider": settings.live2d_provider,
                    "enable_live2d_runtime": settings.enable_live2d_runtime,
                },
            )
        except Exception as exc:
            logger.exception("Live2D dispatcher init failed: %s", exc)
            live2d_dispatcher = NoopLive2DDispatcher()
            capabilities.mark_degraded(
                "live2d_output",
                "Live2D dispatcher failed to initialize. Falling back to noop dispatcher.",
                details={"provider": settings.live2d_provider},
                error=exc,
            )

    output_broadcaster = OutputBroadcaster(
        tts_dispatcher=tts_dispatcher, 
        live2d_dispatcher=live2d_dispatcher, # type: ignore
        motion_policy=MotionPolicy(),
        audio_playback_dispatcher=audio_playback_dispatcher,
        enable_local_audio_playback=settings.enable_local_audio_playback,
    )

    try:
        asr_provider = settings.asr_provider.strip().lower()

        if settings.enable_mock_asr or asr_provider == "mock":
            asr_client = MockASRClient()
            capabilities.mark_degraded(
                "asr",
                "ASR uses mock provider.",
                details={
                    "provider": settings.asr_provider,
                    "mock": True,
                },
            )
        elif asr_provider == "api":
            asr_client = ApiASRClient(
                base_url=settings.asr_api_base_url,
                api_key=settings.asr_api_key,
                model=settings.asr_model,
                language=settings.asr_language,
                timeout_seconds=settings.asr_timeout_seconds,
            )
            capabilities.mark_available(
                "asr",
                "ASR API client is configured.",
                details={
                    "provider": settings.asr_provider,
                    "model": settings.asr_model,
                    "base_url": settings.asr_api_base_url,
                },
            )
        else:
            asr_client = FasterWhisperClient(
                model_size=settings.asr_model_size,
                model_path=settings.asr_model_path,
                device=settings.asr_device,
                compute_type=settings.asr_compute_type,
                language=settings.asr_language,
            )
            capabilities.mark_available(
                "asr",
                "Faster Whisper ASR client is configured.",
                details={
                    "provider": settings.asr_provider,
                    "model_size": settings.asr_model_size,
                    "model_path": settings.asr_model_path,
                    "device": settings.asr_device,
                },
            )
    except Exception as exc:
        logger.exception("ASR client init failed: %s", exc)
        asr_client = MockASRClient()
        capabilities.mark_degraded(
            "asr",
            "ASR client failed to initialize. Falling back to mock ASR.",
            details={"provider": settings.asr_provider},
            error=exc,
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
        shared_state_store=shared_state_store,
    )
    capabilities.mark_available(
        "runtime",
        "Runtime build completed.",
    )

    return CoreRuntime(
        dispatcher=dispatcher,
        agent_core=agent_core,
        speaking_state=speaking_state,
        asr_listener=asr_listener,
        stream_state=streaming_state,
        long_term_memory=long_term_memory, # type: ignore
        memory_runner=memory_runner,
        source_router=source_router,
        llm_service=llm_service,
        conversation_state=conversation_state,
        dialogue_manager=dialogue_manager,
        interrupt_manager=interrupt_manager,
        rag_pipeline=rag_pipeline, # type: ignore
        voice_turn_manager=voice_turn_manager,
        voice_session_controller=voice_session_controller,
        vision_service=vision_service,
        vision_runner=vision_runner,
        capabilities=capabilities,
    )
