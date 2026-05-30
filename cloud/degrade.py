from __future__ import annotations

from typing import Any

from apps.api.request_context import get_request_id


def degraded_chat_response(
    *,
    stage: str,
    error: str,
    user_text: str = "",
    retry_after_seconds: int = 5,
) -> dict[str, Any]:
    fallback_reply = "唉唉唉，阿绫这边有点忙，稍后再回复你哦"

    if user_text.strip():
        fallback_reply = "唉唉唉，阿绫这边有点忙，稍后再回复你哦"

    return {
        "ok": False,
        "stage": stage,
        "error": error,
        "retry_after_seconds": retry_after_seconds,
        "request_id": get_request_id(),
        "degraded": True,
        "reply": fallback_reply,
        "base_reply_text": fallback_reply,
        "emotion": "neutral",
        "motion": "idle",
        "expression": "neutral",
        "audio_path": None,
        "audio_url": None,
        "audio_segments": [],
        "audio_segment_urls": [],
        "audio_segment_texts": [],
        "live2d_command_path": None,
        "live2d": {
            "character": {
                "character_id": "yzl",
                "model_id": "yzl_v1",
                "emotion": "neutral",
                "expression": "neutral",
                "motion": "idle",
                "motion_priority": 0,
                "mouth": {
                    "mode": "idle",
                    "audio_url": "",
                },
                "eye": {
                    "blink": True,
                    "look_at": "user",
                },
            },
            "scene": {
                "background_id": "room_default",
                "lighting": "normal",
                "effect": "none",
            },
        },
        "metadata": {
            "degraded_stage": stage,
            "degraded_error": error,
        },
    }