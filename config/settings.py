from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.defaults import (
    APP_ENV,
    APP_NAME,
    DEFAULT_PERSONA_DESCRIPTION,
    DEFAULT_PERSONA_NAME,
    DEFAULT_PERSONA_RULES,
    DEFAULT_PERSONA_STYLE,
    ENABLE_MOCK_LLM,
    ENABLE_MOCK_PLANNER,
    ENABLE_MOCK_STATE,
    LLM_MODEL,
    LLM_PROVIDER,
    LOG_LEVEL,
    PLANNER_MODEL,
    PLANNER_PROVIDER,
    STATE_MODEL,
    STATE_PROVIDER,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = APP_NAME
    app_env: str = APP_ENV
    log_level: str = LOG_LEVEL

    llm_provider: str = LLM_PROVIDER
    llm_model: str = LLM_MODEL
    enable_mock_llm: bool = ENABLE_MOCK_LLM

    state_provider: str = STATE_PROVIDER
    state_model: str = STATE_MODEL
    enable_mock_state: bool = ENABLE_MOCK_STATE

    planner_provider: str = PLANNER_PROVIDER
    planner_model: str = PLANNER_MODEL
    enable_mock_planner: bool = ENABLE_MOCK_PLANNER

    llm_timeout_seconds: float = Field(default=20.0, alias="LLM_TIMEOUT_SECONDS")
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=200, alias="LLM_MAX_TOKENS")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    siliconflow_api_key: str | None = Field(default=None, alias="SILICONFLOW_API")
    siliconflow_base_url: str = Field(default="https://api.siliconflow.cn/v1", alias="SILICONFLOW_BASE_URL")

    lmstudio_api_key: str | None = Field(default="lm-studio", alias="LMSTUDIO_API_KEY")
    lmstudio_base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="LMSTUDIO_BASE_URL")

    tts_provider: str = Field(default="mock", alias="TTS_PROVIDER")
    enable_mock_tts: bool = Field(default=True, alias="ENABLE_MOCK_TTS")
    tts_timeout_seconds: float = Field(default=60.0, alias="TTS_TIMEOUT_SECONDS")

    gpt_sovits_base_url: str = Field(default="http://127.0.0.1:9880", alias="GPT_SOVITS_BASE_URL")
    gpt_sovits_ref_audio_path: str = Field(default="", alias="GPT_SOVITS_REF_AUDIO_PATH")
    gpt_sovits_prompt_text: str = Field(default="你好，欢迎来到直播间。", alias="GPT_SOVITS_PROMPT_TEXT")
    gpt_sovits_prompt_lang: str = Field(default="zh", alias="GPT_SOVITS_PROMPT_LANG")
    gpt_sovits_text_lang: str = Field(default="zh", alias="GPT_SOVITS_TEXT_LANG")

    indextts2_base_url: str = Field(default="http://127.0.0.1:8000", alias="INDEX_TTS2_BASE_URL")
    indextts2_ref_audio_path: str = Field(default="", alias="INDEX_TTS2_REF_AUDIO_PATH")
    indextts2_emo_alpha: float = Field(default=0.6, alias="INDEX_TTS2_EMO_ALPHA")
    indextts2_use_emo_text: bool = Field(default=True, alias="INDEX_TTS2_USE_EMO_TEXT")
    indextts2_max_segment_length: int = Field(default=20, alias="INDEX_TTS2_MAX_SEGMENT_LENGTH")

    voxcpm_base_url: str = Field(
        default="https://o6n-imn2w3i0x0vlqyxo7-lq7eqede-custom.service.onethingrobot.com",
        alias="VOXCPM_BASE_URL",
    )

    asr_provider: str = Field(default="mock", alias="ASR_PROVIDER")
    enable_mock_asr: bool = Field(default=True, alias="ENABLE_MOCK_ASR")
    asr_model_size: str = Field(default="medium", alias="ASR_MODEL_SIZE")
    asr_model_path: str = Field(default="", alias="ASR_MODEL_PATH")
    asr_device: str = Field(default="cpu", alias="ASR_DEVICE")
    asr_compute_type: str = Field(default="int8", alias="ASR_COMPUTE_TYPE")
    asr_language: str = Field(default="zh", alias="ASR_LANGUAGE")
    asr_sample_rate: int = Field(default=16000, alias="ASR_SAMPLE_RATE")
    asr_record_seconds: int = Field(default=10, alias="ASR_RECORD_SECONDS")

    voice_chunk_seconds: float = Field(default=0.25, alias="VOICE_CHUNK_SECONDS")
    voice_max_record_seconds: float = Field(default=8.0, alias="VOICE_MAX_RECORD_SECONDS")
    voice_silence_seconds: float = Field(default=1.2, alias="VOICE_SILENCE_SECONDS")
    voice_energy_threshold: float = Field(default=0.015, alias="VOICE_ENERGY_THRESHOLD")

    rag_embedding_provider: str = Field(default="huggingface", alias="RAG_EMBEDDING_PROVIDER")
    rag_embedding_model_name: str = Field(default="BAAI/bge-small-zh-v1.5", alias="RAG_EMBEDDING_MODEL_NAME")
    rag_embedding_model_path: str = Field(default="", alias="RAG_EMBEDDING_MODEL_PATH")
    rag_embedding_device: str = Field(default="cpu", alias="RAG_EMBEDDING_DEVICE")
    rag_embedding_local_files_only: bool = Field(default=True, alias="RAG_EMBEDDING_LOCAL_FILES_ONLY")
    rag_embedding_api_key_env: str | None = Field(default=None, alias="RAG_EMBEDDING_API_KEY_ENV")
    rag_embedding_base_url: str | None = Field(default=None, alias="RAG_EMBEDDING_BASE_URL")
    rag_embedding_batch_size: int = Field(default=64, alias="RAG_EMBEDDING_BATCH_SIZE")
    rag_embedding_dimensions: int | None = Field(default=None, alias="RAG_EMBEDDING_DIMENSIONS")

    rag_chunk_size: int = Field(default=520, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=80, alias="RAG_CHUNK_OVERLAP")
    rag_bm25_top_k: int = Field(default=6, alias="RAG_BM25_TOP_K")
    rag_vector_top_k: int = Field(default=6, alias="RAG_VECTOR_TOP_K")
    rag_final_top_k: int = Field(default=4, alias="RAG_FINAL_TOP_K")

    vision_provider: str = Field(default="mock", alias="VISION_PROVIDER")
    vision_model: str = Field(default="", alias="VISION_MODEL")
    vision_api_key_env: str | None = Field(default=None, alias="VISION_API_KEY_ENV")
    vision_base_url: str = Field(default="", alias="VISION_BASE_URL")
    vision_timeout_seconds: float = Field(default=60.0, alias="VISION_TIMEOUT_SECONDS")

    vision_upload_dir: str = Field(default="data/uploads/images", alias="VISION_UPLOAD_DIR")
    vision_max_image_bytes: int = Field(default=12582912, alias="VISION_MAX_IMAGE_BYTES")

    vision_character_root_dir: str = Field(
        default="data/vision/characters",
        alias="VISION_CHARACTER_ROOT_DIR",
    )
    vision_character_index_dir: str = Field(
        default="data/cache/vision/character_index",
        alias="VISION_CHARACTER_INDEX_DIR",
    )
    vision_character_embedding_model_name: str = Field(
        default="clip-ViT-B-32",
        alias="VISION_CHARACTER_EMBEDDING_MODEL_NAME",
    )
    vision_character_embedding_model_path: str = Field(
        default="",
        alias="VISION_CHARACTER_EMBEDDING_MODEL_PATH",
    )
    vision_character_embedding_device: str = Field(
        default="cpu",
        alias="VISION_CHARACTER_EMBEDDING_DEVICE",
    )
    vision_character_embedding_local_files_only: bool = Field(
        default=False,
        alias="VISION_CHARACTER_EMBEDDING_LOCAL_FILES_ONLY",
    )
    vision_character_confident_score: float = Field(
        default=0.78,
        alias="VISION_CHARACTER_CONFIDENT_SCORE",
    )




    memory_llm_provider: str = Field(default="openai", alias="MEMORY_LLM_PROVIDER")
    memory_llm_model: str = Field(default="gpt-4o-mini", alias="MEMORY_LLM_MODEL")
    memory_llm_api_key_env: str = Field(default="OPENAI_API_KEY", alias="MEMORY_LLM_API_KEY_ENV")

    memory_embedder_provider: str = Field(default="openai", alias="MEMORY_EMBEDDER_PROVIDER")
    memory_embedder_model: str = Field(default="text-embedding-3-small", alias="MEMORY_EMBEDDER_MODEL")
    memory_embedder_api_key_env: str | None = Field(default="OPENAI_API_KEY", alias="MEMORY_EMBEDDER_API_KEY_ENV")

    memory_vector_provider: str = Field(default="qdrant", alias="MEMORY_VECTOR_PROVIDER")
    memory_vector_collection: str = Field(default="aiagent_long_term_memory", alias="MEMORY_VECTOR_COLLECTION")
    memory_embedding_dims: int = Field(default=1536, alias="MEMORY_EMBEDDING_DIMS")

    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")

    memory_enable_graph: bool = Field(default=False, alias="MEMORY_ENABLE_GRAPH")
    memory_graph_provider: str = Field(default="neo4j", alias="MEMORY_GRAPH_PROVIDER")
    neo4j_url: str = Field(default="bolt://localhost:7687", alias="NEO4J_URL")
    neo4j_username: str = Field(default="neo4j", alias="NEO4J_USERNAME")
    neo4j_password: str | None = Field(default=None, alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")

    memory_reset_vector_store: bool = Field(default=False, alias="MEMORY_RESET_VECTOR_STORE")

    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="API_CORS_ORIGINS",
    )

    persona_name: str = DEFAULT_PERSONA_NAME
    persona_description: str = DEFAULT_PERSONA_DESCRIPTION
    persona_style: str = DEFAULT_PERSONA_STYLE
    persona_rules: str = DEFAULT_PERSONA_RULES

    live2d_provider: str = Field(default="mock", alias="LIVE2D_PROVIDER")
    enable_live2d_runtime: bool = Field(default=False, alias="ENABLE_LIVE2D_RUNTIME")


    @field_validator("rag_embedding_dimensions", mode="before")
    @classmethod
    def _empty_rag_embedding_dimensions_to_none(cls, value):
        if value == "":
            return None
        return value

    @field_validator("memory_embedding_dims", mode="before")
    @classmethod
    def _empty_memory_embedding_dims_to_default(cls, value):
        if value == "":
            return 1536
        return value


settings = Settings()
