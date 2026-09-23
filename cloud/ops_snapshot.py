from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cloud.config import cloud_settings
from config.settings import settings


SENSITIVE_KEY_PARTS = {
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "access_key",
    "private_key",
}

WEAK_PLACEHOLDER_PARTS = {
    "change",
    "changeme",
    "your-",
    "replace",
    "example",
    "demo",
    "test-token",
    "unit-token",
}


def build_config_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "cloud": _cloud_snapshot(),
        "security": _security_snapshot(),
        "redis": _redis_snapshot(),
        "storage": _storage_snapshot(),
        "gpu": _gpu_snapshot(),
        "limits": _limits_snapshot(),
        "paths": _paths_snapshot(),
        "risk_summary": _risk_summary(),
    }


def sanitize_config_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return _redacted_secret_state(value)

    if isinstance(value, dict):
        return {
            str(item_key): sanitize_config_value(str(item_key), item_value)
            for item_key, item_value in value.items()
        }

    if isinstance(value, list):
        return [
            sanitize_config_value(key, item)
            for item in value
        ]

    return value


def admin_token_state(value: str | None = None) -> dict[str, Any]:
    token = (value if value is not None else os.getenv("CLOUD_ADMIN_TOKEN", "")).strip()
    configured = bool(token)
    weak_reasons: list[str] = []

    if not configured:
        weak_reasons.append("missing")
    else:
        lowered = token.lower()
        if len(token) < 16:
            weak_reasons.append("too_short")
        if any(part in lowered for part in WEAK_PLACEHOLDER_PARTS):
            weak_reasons.append("placeholder_like")

    return {
        "configured": configured,
        "strong": configured and not weak_reasons,
        "length": len(token) if configured else 0,
        "weak_reasons": weak_reasons,
    }


def _cloud_snapshot() -> dict[str, Any]:
    return {
        "cloud_mode": cloud_settings.cloud_mode,
        "region": cloud_settings.cloud_deploy_region,
        "api_public_base_url_configured": bool(cloud_settings.api_public_base_url),
    }


def _security_snapshot() -> dict[str, Any]:
    return {
        "admin_token": admin_token_state(),
        "admin_header": "x-cloud-admin-token",
        "legacy_admin_header_supported": True,
        "cors": _cors_snapshot(),
    }


def _cors_origins() -> list[str]:
    """把逗号分隔的 API_CORS_ORIGINS 解析成列表，并统一去掉尾部斜杠。"""
    raw = str(getattr(settings, "api_cors_origins", "") or "")
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def _cors_snapshot() -> dict[str, Any]:
    origins = _cors_origins()
    loopback = [
        item for item in origins
        if item.startswith(
            ("http://localhost", "https://localhost", "http://127.0.0.1", "http://0.0.0.0")
        )
    ]

    return {
        "origins": origins,
        "origin_count": len(origins),
        "wildcard": any(item == "*" for item in origins),
        "loopback_origins": loopback,
        "allow_credentials": bool(getattr(settings, "api_cors_allow_credentials", False)),
    }


def _redis_snapshot() -> dict[str, Any]:
    return {
        "configured": bool(cloud_settings.redis_url),
        "prefix": cloud_settings.redis_prefix,
        "required": bool(cloud_settings.cloud_mode),
    }


def _storage_snapshot() -> dict[str, Any]:
    provider = cloud_settings.storage_provider.strip().lower()

    return sanitize_config_value(
        "storage",
        {
            "provider": provider,
            "local_storage_root": cloud_settings.local_storage_root,
            "upload_max_bytes": cloud_settings.upload_max_bytes,
            "s3_endpoint_url_configured": bool(cloud_settings.s3_endpoint_url),
            "s3_region": cloud_settings.s3_region,
            "s3_bucket_configured": bool(cloud_settings.s3_bucket),
            "s3_public_base_url_configured": bool(cloud_settings.s3_public_base_url),
            "s3_access_key_id": cloud_settings.s3_access_key_id,
            "s3_secret_access_key": cloud_settings.s3_secret_access_key,
        },
    )


def _gpu_snapshot() -> dict[str, Any]:
    return {
        "llm_base_url_configured": bool(cloud_settings.gpu_llm_base_url),
        "tts_base_url_configured": bool(cloud_settings.gpu_tts_base_url),
        "asr_base_url_configured": bool(cloud_settings.gpu_asr_base_url),
        "gpu_api_token": _redacted_secret_state(os.getenv("GPU_API_TOKEN", "")),
    }


def _limits_snapshot() -> dict[str, Any]:
    return {
        "rate_limit_enabled": cloud_settings.rate_limit_enabled,
        "inflight_limit_enabled": cloud_settings.inflight_limit_enabled,
        "limiter_fail_open": cloud_settings.limiter_fail_open,
        "rate_limit": {
            "default_per_minute": cloud_settings.rate_limit_default_per_minute,
            "chat_per_minute": cloud_settings.rate_limit_chat_per_minute,
            "multimodal_per_minute": cloud_settings.rate_limit_multimodal_per_minute,
            "voice_per_minute": cloud_settings.rate_limit_voice_per_minute,
            "rebuild_per_minute": cloud_settings.rate_limit_rebuild_per_minute,
        },
        "inflight": {
            "global": cloud_settings.global_inflight_limit,
            "chat": cloud_settings.chat_inflight_limit,
            "multimodal": cloud_settings.multimodal_inflight_limit,
            "voice": cloud_settings.voice_inflight_limit,
            "rebuild": cloud_settings.rebuild_inflight_limit,
            "lease_seconds": cloud_settings.inflight_lease_seconds,
        },
    }


def _paths_snapshot() -> dict[str, Any]:
    return {
        "data": _path_status("data"),
        "cache": _path_status("data/cache"),
        "knowledge": _path_status("data/knowledge"),
        "characters": _path_status("data/characters"),
        "cloud_storage": _path_status(cloud_settings.local_storage_root),
    }


def _path_status(path: str) -> dict[str, Any]:
    target = Path(path)
    return {
        "path": path,
        "exists": target.exists(),
        "is_dir": target.is_dir(),
    }


def _risk_summary() -> dict[str, Any]:
    risks: list[dict[str, str]] = []

    admin = admin_token_state()
    if not admin["configured"]:
        risks.append(
            {
                "level": "critical",
                "key": "cloud_admin_token_missing",
                "message": "CLOUD_ADMIN_TOKEN is not configured.",
            }
        )
    elif not admin["strong"]:
        risks.append(
            {
                "level": "high",
                "key": "cloud_admin_token_weak",
                "message": "CLOUD_ADMIN_TOKEN looks weak or placeholder-like.",
            }
        )

    if cloud_settings.cloud_mode and not cloud_settings.redis_url:
        risks.append(
            {
                "level": "critical",
                "key": "redis_required_in_cloud_mode",
                "message": "CLOUD_MODE=true requires REDIS_URL for shared cloud coordination.",
            }
        )

    if cloud_settings.cloud_mode and not cloud_settings.rate_limit_enabled:
        risks.append(
            {
                "level": "high",
                "key": "rate_limit_disabled_in_cloud_mode",
                "message": "RATE_LIMIT_ENABLED should be true in cloud mode.",
            }
        )

    if cloud_settings.cloud_mode and not cloud_settings.inflight_limit_enabled:
        risks.append(
            {
                "level": "high",
                "key": "inflight_limit_disabled_in_cloud_mode",
                "message": "INFLIGHT_LIMIT_ENABLED should be true in cloud mode.",
            }
        )

    provider = cloud_settings.storage_provider.strip().lower()
    if provider not in {"local", "s3", "cos"}:
        risks.append(
            {
                "level": "critical",
                "key": "unsupported_storage_provider",
                "message": "STORAGE_PROVIDER must be local, s3 or cos.",
            }
        )

    if provider in {"s3", "cos"}:
        if not cloud_settings.s3_bucket:
            risks.append(
                {
                    "level": "critical",
                    "key": "s3_bucket_missing",
                    "message": "S3_BUCKET is required when STORAGE_PROVIDER=s3/cos.",
                }
            )

        if not cloud_settings.s3_access_key_id or not cloud_settings.s3_secret_access_key:
            risks.append(
                {
                    "level": "critical",
                    "key": "s3_credentials_missing",
                    "message": "S3/COS credentials are required when STORAGE_PROVIDER=s3/cos.",
                }
            )

    cors = _cors_snapshot()

    # 通配符 + 携带凭据：浏览器本身就会拒绝，且等于放弃 Origin 隔离。
    if cors["wildcard"] and cors["allow_credentials"]:
        risks.append(
            {
                "level": "critical",
                "key": "cors_wildcard_with_credentials",
                "message": "API_CORS_ORIGINS contains '*' while credentials are allowed.",
            }
        )
    # 云模式仍保留 loopback origin：本地调试配置被带到生产的典型症状。
    elif cloud_settings.cloud_mode and cors["allow_credentials"] and cors["loopback_origins"]:
        risks.append(
            {
                "level": "high",
                "key": "cors_loopback_origins_in_cloud_mode",
                "message": (
                    "CLOUD_MODE=true but API_CORS_ORIGINS still contains loopback origins "
                    "while credentials are allowed."
                ),
            }
        )

    return {
        "count": len(risks),
        "critical": sum(1 for item in risks if item["level"] == "critical"),
        "high": sum(1 for item in risks if item["level"] == "high"),
        "items": risks,
    }


def _redacted_secret_state(value: Any) -> dict[str, Any]:
    text = "" if value is None else str(value)
    configured = bool(text.strip())

    return {
        "configured": configured,
        "redacted": "[redacted]" if configured else "",
        "length": len(text.strip()) if configured else 0,
    }


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)