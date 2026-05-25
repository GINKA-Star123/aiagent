from __future__ import annotations

from datetime import datetime, timezone

from aiagent.presence.models import OpeningKind, SessionSnapshot
from aiagent.presence.rhythm import mood_label


def choose_opening_kind(now: datetime, snapshot: SessionSnapshot) -> OpeningKind:
    if snapshot.open_count <= 0 or snapshot.last_opened_at is None:
        return "first_meet"

    delta = now - snapshot.last_opened_at
    seconds = delta.total_seconds()

    if snapshot.unfinished_hint.strip():
        return "task_resume"

    if now.hour >= 23 or now.hour < 5:
        return "late_night"

    if seconds < 10 * 60:
        return "short_return"

    if now.date() == snapshot.last_opened_at.date():
        return "same_day_return"

    if seconds < 60 * 60 * 48:
        return "next_day_return"

    return "long_absence"


def generate_opening_text(
    *,
    kind: OpeningKind,
    now: datetime,
    snapshot: SessionSnapshot,
) -> str:
    label = mood_label(snapshot.mood)
    topic = snapshot.last_topic.strip()
    unfinished = snapshot.unfinished_hint.strip()

    if kind == "first_meet":
        return "你好,该是说初次见面呢，还是好久不见呢。我是乐正绫"

    if kind == "short_return":
        if topic:
            return f"回来了？我还停在刚刚那个话题上：{topic}。"
        return "回来了？我还在这儿，刚刚没有走远。"

    if kind == "same_day_return":
        if topic:
            return f"你来了。我刚刚还在想我们今天聊到的「{topic}」。"
        return "你来了。我刚刚在安静待机，看到你回来就精神了一点。"

    if kind == "next_day_return":
        if topic:
            return f"今天也来了。我记得上次我们聊到「{topic}」，要继续吗？"
        return "今天也来了。我刚刚在整理状态，正好可以陪你继续。"

    if kind == "long_absence":
        if topic:
            return f"好久不见。我还留着上次那个话题：「{topic}」。"
        return "好久不见。我这边一直保持着状态，等你回来继续。"

    if kind == "late_night":
        if label == "sleepy":
            return "这么晚还在啊。我现在是低能量模式，不过可以小声陪你。"
        return "这么晚打开，我就把状态调安静一点。你想聊什么？"

    if kind == "task_resume":
        return f"你来了。我记得还有一件事没收尾：{unfinished}"

    return "你来了。我在。"


def update_snapshot_after_open(
    *,
    snapshot: SessionSnapshot,
    now: datetime,
    recent_topic: str = "",
) -> SessionSnapshot:
    next_snapshot = snapshot.model_copy(deep=True)
    next_snapshot.open_count += 1
    next_snapshot.last_opened_at = now.astimezone(timezone.utc)

    if recent_topic.strip():
        next_snapshot.last_topic = recent_topic.strip()[:120]

    return next_snapshot