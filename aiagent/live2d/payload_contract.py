from __future__ import annotations

from typing import Any

from aiagent.live2d.models import (
    LIVE2D_PAYLOAD_VERSION,
    Live2DCharacterCommand,
    Live2DPayload,
    Live2DSceneCommand,
)

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
    raw = _as_dict(payload)
    character_raw = _as_dict(raw.get("character"))
    scene_raw = _as_dict(raw.get("scene"))

    mouth_raw = _as_dict(character_raw.get("mouth"))
    eye_raw = _as_dict(character_raw.get("eye"))

    resolved_audio_url = _text(mouth_raw.get("audio_url") or audio_url)
    mouth_mode = _text(mouth_raw.get("mode"))
    if not mouth_mode:
        mouth_mode = "audio" if resolved_audio_url else "idle"

    normalized = Live2DPayload(
        version=_text(raw.get("version") or LIVE2D_PAYLOAD_VERSION),
        character=Live2DCharacterCommand(
            character_id=_text(character_raw.get("character_id") or "yzl"),
            model_id=_text(character_raw.get("model_id") or "yzl_v1"),
            display_name=_text(character_raw.get("display_name")),
            model3_json=_text(character_raw.get("model3_json")),
            emotion=_text(character_raw.get("emotion") or emotion or "neutral"),
            expression=_text(character_raw.get("expression") or expression or "neutral"),
            expression_file=_text(character_raw.get("expression_file")),
            motion=_text(character_raw.get("motion") or motion or "idle"),
            motion_group=_text(character_raw.get("motion_group") or "default"),
            motion_file=_text(character_raw.get("motion_file")),
            motion_priority=_int_value(character_raw.get("motion_priority"), 1),
            mouth={
                "mode": mouth_mode,
                "audio_url": resolved_audio_url,
            },
            eye={
                "blink": eye_raw.get("blink") is not False,
                "look_at": _text(eye_raw.get("look_at") or "user"),
            },
            metadata=_as_dict(character_raw.get("metadata")),
        ),
        scene=Live2DSceneCommand(
            background_id=_text(scene_raw.get("background_id") or background_id or "room_default"),
            background_file=_text(scene_raw.get("background_file")),
            lighting=_text(scene_raw.get("lighting") or "normal"),
            effect=_text(scene_raw.get("effect") or "none"),
            metadata=_as_dict(scene_raw.get("metadata")),
        ),
        metadata={
            **_as_dict(raw.get("metadata")),
            **_as_dict(metadata),
        },
    )

    return normalized.model_dump(mode="json")


def _as_dict(value: Any) -> dict[str,Any]:
    if isinstance(value,dict):
        return dict(value)

    return {}

def _text(value:Any) ->str:
    if value is None:
        return ""
    return str(value).strip()

def _int_value(value:Any,fallback:int) ->int:
    try:
        return int(value)
    except Exception :
        return fallback