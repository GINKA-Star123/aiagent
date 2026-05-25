from __future__ import annotations

from aiagent.presence.models import Live2DPresencePayload, OpeningKind, PresenceState
from aiagent.presence.rhythm import mood_label
from aiagent.presence.models import MoodState


def build_live2d_presence(
    *,
    state: PresenceState,
    kind: OpeningKind,
    mood: MoodState,
) -> Live2DPresencePayload:
    label = mood_label(mood)

    expression = "neutral"
    motion = "idle"
    delay_ms = 600

    if kind == "first_meet":
        expression = "soft_smile"
        motion = "wave_small"
        delay_ms = 700

    elif kind == "short_return":
        expression = "soft_smile"
        motion = "look_at_user"
        delay_ms = 350

    elif kind == "same_day_return":
        expression = "smile"
        motion = "look_up"
        delay_ms = 600

    elif kind == "next_day_return":
        expression = "soft_smile"
        motion = "wave_small"
        delay_ms = 800

    elif kind == "long_absence":
        expression = "surprised_soft"
        motion = "look_up_wave"
        delay_ms = 900

    elif kind == "late_night":
        expression = "sleepy_soft"
        motion = "slow_blink"
        delay_ms = 900

    elif kind == "task_resume":
        expression = "focused"
        motion = "think_to_user"
        delay_ms = 750

    if state == "working":
        motion = "look_down_then_user"
    elif state == "reading":
        motion = "reading_to_user"
    elif state == "focused":
        expression = "focused"
    elif state == "sleepy":
        expression = "sleepy_soft"
        delay_ms = max(delay_ms, 900)

    if label == "bright":
        expression = "smile"
        delay_ms = max(300, delay_ms - 150)
    elif label == "warm":
        expression = "soft_smile"
    elif label == "quiet":
        expression = "neutral_soft"

    return Live2DPresencePayload(
        expression=expression,
        motion=motion,
        suggested_delay_ms=delay_ms,
        eye={
            "blink": True,
            "look_at": "user",
        },
        mouth={
            "mode": "tts",
        },
        scene={
            "background_id": _scene_for_state(state),
            "lighting": _lighting_for_state(state),
            "effect": "none",
        },
    )


def _scene_for_state(state: PresenceState) -> str:
    if state in {"working", "focused", "reading"}:
        return "desk_default"
    if state == "sleepy":
        return "room_night"
    if state == "resting":
        return "room_soft"
    return "room_default"


def _lighting_for_state(state: PresenceState) -> str:
    if state == "sleepy":
        return "dim"
    if state in {"working", "focused"}:
        return "normal"
    return "soft"