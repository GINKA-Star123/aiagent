from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.defaults import (
    APP_ENV,
    APP_NAME,
    DEFAULT_PERSONA_DESCRIPTION,
    DEFAULT_PERSONA_NAME,
    DEFAULT_PERSONA_RULES,
    DEFAULT_PERSONA_STYLE,
    ENABLE_MOCK_LLM,
    ENABLE_MOCK_STATE,
    ENABLE_MOCK_PLANNER,
    LLM_MODEL,
    LLM_PROVIDER,
    STATE_PROVIDER,
    STATE_MODEL,
    PLANNER_MODEL,
    PLANNER_PROVIDER,
    LOG_LEVEL,
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

    planner_provider :str = PLANNER_PROVIDER
    planner_model :str = PLANNER_MODEL
    enable_mock_planner :bool =ENABLE_MOCK_PLANNER

    llm_timeout_seconds: float = 20.0
    llm_temperature: float = 0.7
    llm_max_tokens: int = 200

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    siliconflow_api_key: str | None = Field(default=None, alias="SILICONFLOW_API")
    siliconflow_base_url: str = Field(default="https://api.siliconflow.cn/v1", alias="SILICONFLOW_BASE_URL")

    lmstudio_api_key: str | None = Field(default="lm-studio", alias="LMSTUDIO_API_KEY")
    lmstudio_base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="LMSTUDIO_BASE_URL")

    tts_provider :str = Field(default="mock",alias = "TTS_PROVIDER")
    enable_mock_tts :bool = Field(default=True,alias ="ENABLE_MOCK_TTS")
    tts_timeout_seconds: float  = Field(default=60.0,alias="TTS_TIMEOUT_SECONDS")
    
    gpt_sovits_base_url : str =Field(default="http://127.0.0.1:9880",alias="GPT_SOVITS_BASE_URL")
    gpt_sovits_ref_audio_path: str = Field(default="", alias="GPT_SOVITS_REF_AUDIO_PATH")
    gpt_sovits_prompt_text: str = Field(default="你好，欢迎来到直播间。", alias="GPT_SOVITS_PROMPT_TEXT")
    gpt_sovits_prompt_lang: str = Field(default="zh", alias="GPT_SOVITS_PROMPT_LANG")
    gpt_sovits_text_lang: str = Field(default="zh", alias="GPT_SOVITS_TEXT_LANG")

    asr_provider : str = Field(default="mock",alias = "ASR_PROVIDER")
    enable_mock_asr : bool = Field(default = True,alias = "ENABLE_MOCK_ASR")
    asr_model_size : str = Field(default="medium",alias = "ASR_MODEL_SIZE")
    asr_model_path: str = Field(default="", alias="ASR_MODEL_PATH")
    asr_device : str = Field(default="cpu",alias = "ASR_DEVICE")
    asr_compute_type :str = Field(default="int8",alias = "ASR_COMPUTE_TYPE")
    asr_language : str = Field(default="zh",alias = "ASR_LANGUAGE")
    asr_sample_rate : int = Field(default=16000,alias = "ASR_SAMPLE_RATE")
    asr_record_seconds :int = Field(default=10,alias = "ASR_RECORD_SECONDS")

    voice_chunk_seconds : float = Field(default=0.25,alias = "VOICE_CHUNK_SECONDS")
    voice_max_record_seconds: float = Field(default=8.0,alias = "VOICE_MAX_RECORD_SECONDS")
    voice_silence_seconds : float =Field(default=1.2,alias = "VOICE_SILENCE_SECONDS")
    voice_energy_threshold : float =Field(default=0.015,alias = "VOICE_ENERGY_THRESHOLD")

    rag_embedding_model_name: str = Field(
        default="BAAI/bge-small-zh-v1.5",
        alias="RAG_EMBEDDING_MODEL_NAME",
    )
    rag_embedding_model_path: str = Field(default="", alias="RAG_EMBEDDING_MODEL_PATH")
    rag_chunk_size : int = Field(default=520,alias = "RAG_CHUNK_SIZE")
    rag_chunk_overlap:int = Field(default=80,alias = "RAG_CHUNK_OVERLAP")
    rag_bm25_top_k : int = Field(default=6,alias = "RAG_BM25_TOP_K")
    rag_vector_top_k : int = Field(default=6,alias = "RAG_VECTOR_TOP_K")
    rag_final_top_k : int = Field(default=4,alias= "RAG_FINAL_TOP_K")

    persona_name: str = DEFAULT_PERSONA_NAME
    persona_description: str = DEFAULT_PERSONA_DESCRIPTION
    persona_style: str = DEFAULT_PERSONA_STYLE
    persona_rules: str = DEFAULT_PERSONA_RULES


settings = Settings()
