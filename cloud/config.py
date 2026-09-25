from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cloud_mode: bool = Field(default=False, alias="CLOUD_MODE")
    cloud_deploy_region: str = Field(default="tencent-cn", alias="CLOUD_DEPLOY_REGION")
    api_public_base_url: str = Field(default="", alias="API_PUBLIC_BASE_URL")

    redis_url: str = Field(default="", alias="REDIS_URL")
    redis_prefix: str = Field(default="aiagent:v1", alias="REDIS_PREFIX")
    voice_call_store_provider: str = Field(
        default="auto",
        alias="VOICE_CALL_STORE_PROVIDER",
    )
    voice_call_store_fail_open: bool = Field(
        default=False,
        alias="VOICE_CALL_STORE_FAIL_OPEN",
    )
    voice_call_ttl_seconds: int = Field(
        default=1800,
        ge=60,
        alias="VOICE_CALL_TTL_SECONDS",
    )
    voice_call_ended_ttl_seconds: int = Field(
        default=300,
        ge=60,
        alias="VOICE_CALL_ENDED_TTL_SECONDS",
    )
    voice_call_lock_ttl_seconds: int = Field(
        default=15,
        ge=3,
        alias="VOICE_CALL_LOCK_TTL_SECONDS",
    )
    voice_call_lock_wait_seconds: float = Field(
        default=2.0,
        ge=0.1,
        alias="VOICE_CALL_LOCK_WAIT_SECONDS",
    )

    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    inflight_limit_enabled: bool = Field(default=False, alias="INFLIGHT_LIMIT_ENABLED")
    limiter_fail_open: bool = Field(default=True, alias="LIMITER_FAIL_OPEN")

    rate_limit_default_per_minute: int = Field(default=60, alias="RATE_LIMIT_DEFAULT_PER_MINUTE")
    rate_limit_chat_per_minute: int = Field(default=20, alias="RATE_LIMIT_CHAT_PER_MINUTE")
    rate_limit_multimodal_per_minute: int = Field(default=5, alias="RATE_LIMIT_MULTIMODAL_PER_MINUTE")
    rate_limit_voice_per_minute: int = Field(default=5, alias="RATE_LIMIT_VOICE_PER_MINUTE")
    rate_limit_rebuild_per_minute: int = Field(default=1, alias="RATE_LIMIT_REBUILD_PER_MINUTE")

    global_inflight_limit: int = Field(default=100, alias="GLOBAL_INFLIGHT_LIMIT")
    chat_inflight_limit: int = Field(default=40, alias="CHAT_INFLIGHT_LIMIT")
    multimodal_inflight_limit: int = Field(default=10, alias="MULTIMODAL_INFLIGHT_LIMIT")
    voice_inflight_limit: int = Field(default=8, alias="VOICE_INFLIGHT_LIMIT")
    rebuild_inflight_limit: int = Field(default=1, alias="REBUILD_INFLIGHT_LIMIT")
    inflight_lease_seconds: int = Field(default=120, alias="INFLIGHT_LEASE_SECONDS")

    storage_provider: str = Field(default="local", alias="STORAGE_PROVIDER")
    local_storage_root: str = Field(default="data/cloud_storage", alias="LOCAL_STORAGE_ROOT")
    upload_max_bytes: int = Field(default=26214400, alias="UPLOAD_MAX_BYTES")

    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    s3_region: str = Field(default="ap-guangzhou", alias="S3_REGION")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")
    s3_public_base_url: str = Field(default="", alias="S3_PUBLIC_BASE_URL")

    gpu_llm_base_url: str = Field(default="", alias="GPU_LLM_BASE_URL")
    gpu_tts_base_url: str = Field(default="", alias="GPU_TTS_BASE_URL")
    gpu_asr_base_url: str = Field(default="", alias="GPU_ASR_BASE_URL")

    execution_state_mode: str = Field(
        default="local",
        alias="EXECUTION_STATE_MODE",
    )
    execution_state_fail_closed: bool = Field(
        default=True,
        alias="EXECUTION_STATE_FAIL_CLOSED",
    )
    execution_state_session_ttl_seconds: int = Field(
        default=86400,
        ge=300,
        alias="EXECUTION_STATE_SESSION_TTL_SECONDS",
    )
    execution_state_thread_ttl_seconds: int = Field(
        default=1800,
        ge=300,
        alias="EXECUTION_STATE_THREAD_TTL_SECONDS",
    )
    execution_state_lock_ttl_seconds: int = Field(
        default=60,
        ge=10,
        alias="EXECUTION_STATE_LOCK_TTL_SECONDS",
    )

    @field_validator("execution_state_mode")
    @classmethod
    def validate_execution_state_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local", "redis"}:
            raise ValueError("EXECUTION_STATE_MODE must be local or redis")
        return normalized

    @field_validator(
        "s3_access_key_id",
        "s3_secret_access_key",
        mode="before",
    )
    @classmethod
    def _empty_secret_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value
    @field_validator(
        "voice_call_store_provider",
        mode="before",
    )
    @classmethod
    def _normalize_voice_call_store_provider(
        cls,
        value: object,
    ) -> str:
        provider = str(value or "auto").strip().lower()

        if provider not in {"auto", "memory", "redis"}:
            raise ValueError(
                "VOICE_CALL_STORE_PROVIDER must be auto, memory or redis"
            )

        return provider


cloud_settings = CloudSettings()