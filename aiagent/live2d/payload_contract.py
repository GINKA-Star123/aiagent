from __future__ import annotations

from typing import Any

from aiagent.live2d.models import (
    LIVE2D_ALLOWED_AUDIO_PREFIXES,
    LIVE2D_EMOTION_VOCABULARY,
    LIVE2D_MAX_TEXT_CHARS,
    LIVE2D_PAYLOAD_VERSION,
    Live2DCharacterCommand,
    Live2DPayload,
    Live2DPayloadWarning,
    Live2DSceneCommand,
)

UNSAFE_PATH_MARKERS = ("..", ":", "\\\\")


def normalize_live2d_payload(
    payload: dict[str, Any] | None,
    *,
    emotion: str = "neutral",
    expression: str = "neutral",
    motion: str = "idle",
    audio_url: str = "",
    background_id: str = "room_default",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把任意来源的 Live2D payload 归一化成稳定契约。

    原则：
    1. 缺字段一律补默认值，客户端不会因为字段缺失崩溃；
    2. 未知的 expression / motion 保持原值（它们是 profile 资产 id），只做清洗；
    3. 未知 emotion 只告警不改写，避免破坏 profile 的 emotion_*_map；
    4. 文件路径与 audio_url 做安全清洗，拒绝路径穿越与非 http(s) 协议；
    5. 所有问题都进 warnings，永不抛异常。
    """
    warnings: list[Live2DPayloadWarning] = []

    raw = _as_dict(payload)
    character_raw = _as_dict(raw.get("character"))
    scene_raw = _as_dict(raw.get("scene"))

    mouth_raw = _as_dict(character_raw.get("mouth"))
    eye_raw = _as_dict(character_raw.get("eye"))

    resolved_audio_url = _safe_audio_url(
        mouth_raw.get("audio_url") or audio_url,
        "character.mouth.audio_url",
        warnings,
    )
    mouth_mode = _safe_text(mouth_raw.get("mode"), "character.mouth.mode", warnings)
    if not mouth_mode:
        mouth_mode = "audio" if resolved_audio_url else "idle"
    elif mouth_mode not in {"idle", "audio", "closed"}:
        warnings.append(
            _warning("character.mouth.mode", "unknown_mouth_mode", f"未知口型模式：{mouth_mode}")
        )

    resolved_emotion = _safe_text(
        character_raw.get("emotion") or emotion or "neutral",
        "character.emotion",
        warnings,
    ) or "neutral"
    if resolved_emotion.lower() not in LIVE2D_EMOTION_VOCABULARY:
        warnings.append(
            _warning(
                "character.emotion",
                "unknown_emotion",
                "emotion 不在语义词表中，将交给 profile 的 emotion_*_map 解析："
                f"{resolved_emotion}",
            )
        )

    normalized = Live2DPayload(
        version=_safe_text(raw.get("version") or LIVE2D_PAYLOAD_VERSION, "version", warnings)
        or LIVE2D_PAYLOAD_VERSION,
        character=Live2DCharacterCommand(
            character_id=_safe_text(
                character_raw.get("character_id") or "yzl", "character.character_id", warnings
            ) or "yzl",
            model_id=_safe_text(
                character_raw.get("model_id") or "yzl_v1", "character.model_id", warnings
            ) or "yzl_v1",
            display_name=_safe_text(
                character_raw.get("display_name"), "character.display_name", warnings
            ),
            model3_json=_safe_asset_path(
                character_raw.get("model3_json"), "character.model3_json", warnings
            ),
            emotion=resolved_emotion,
            expression=_safe_text(
                character_raw.get("expression") or expression or "neutral",
                "character.expression",
                warnings,
            ) or "neutral",
            expression_file=_safe_asset_path(
                character_raw.get("expression_file"), "character.expression_file", warnings
            ),
            motion=_safe_text(
                character_raw.get("motion") or motion or "idle", "character.motion", warnings
            ) or "idle",
            motion_group=_safe_text(
                character_raw.get("motion_group") or "default", "character.motion_group", warnings
            ) or "default",
            motion_file=_safe_asset_path(
                character_raw.get("motion_file"), "character.motion_file", warnings
            ),
            motion_priority=_int_value(
                character_raw.get("motion_priority"), 1, "character.motion_priority", warnings
            ),
            mouth={
                "mode": mouth_mode,
                "audio_url": resolved_audio_url,
            },
            eye={
                "blink": eye_raw.get("blink") is not False,
                "look_at": _safe_text(
                    eye_raw.get("look_at") or "user", "character.eye.look_at", warnings
                ) or "user",
            },
            metadata=_as_dict(character_raw.get("metadata")),
        ),
        scene=Live2DSceneCommand(
            background_id=_safe_text(
                scene_raw.get("background_id") or background_id or "room_default",
                "scene.background_id",
                warnings,
            ) or "room_default",
            background_file=_safe_asset_path(
                scene_raw.get("background_file"), "scene.background_file", warnings
            ),
            lighting=_safe_text(
                scene_raw.get("lighting") or "normal", "scene.lighting", warnings
            ) or "normal",
            effect=_safe_text(
                scene_raw.get("effect") or "none", "scene.effect", warnings
            ) or "none",
            metadata=_as_dict(scene_raw.get("metadata")),
        ),
        metadata={
            **_as_dict(raw.get("metadata")),
            **_as_dict(metadata),
        },
        warnings=warnings,
    )

    return normalized.model_dump(mode="json")


def _warning(path: str, code: str, detail: str) -> Live2DPayloadWarning:
    return Live2DPayloadWarning(path=path, code=code, detail=str(detail)[:200])


def _safe_text(value: Any, path: str, warnings: list[Live2DPayloadWarning]) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""

    text = "".join(ch for ch in str(value) if ch >= " ").strip()
    if len(text) > LIVE2D_MAX_TEXT_CHARS:
        warnings.append(
            _warning(path, "field_truncated", f"{path} 超过 {LIVE2D_MAX_TEXT_CHARS} 字符，已截断")
        )
        text = text[:LIVE2D_MAX_TEXT_CHARS]

    return text


def _safe_asset_path(value: Any, path: str, warnings: list[Live2DPayloadWarning]) -> str:
    text = _safe_text(value, path, warnings)
    if not text:
        return ""

    if any(marker in text for marker in UNSAFE_PATH_MARKERS) or text.startswith("/"):
        warnings.append(
            _warning(path, "unsafe_asset_path", f"{path} 含绝对路径或上级目录片段，已清空")
        )
        return ""

    return text


def _safe_audio_url(value: Any, path: str, warnings: list[Live2DPayloadWarning]) -> str:
    text = _safe_text(value, path, warnings)
    if not text:
        return ""

    lowered = text.lower()
    if lowered.startswith(("javascript:", "data:", "file:", "vbscript:")):
        warnings.append(_warning(path, "unsafe_audio_url", f"{path} 协议不被允许，已清空"))
        return ""

    if not lowered.startswith(LIVE2D_ALLOWED_AUDIO_PREFIXES):
        warnings.append(
            _warning(path, "unsafe_audio_url", f"{path} 不是站内路径或 http(s) 地址，已清空")
        )
        return ""

    return text


def _int_value(
    value: Any,
    fallback: int,
    path: str,
    warnings: list[Live2DPayloadWarning],
) -> int:
    try:
        return int(value)
    except Exception:
        if value is not None and value != "":
            warnings.append(
                _warning(path, "invalid_int", f"{path} 不是整数，已回退为 {fallback}")
            )
        return fallback


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    return {}
