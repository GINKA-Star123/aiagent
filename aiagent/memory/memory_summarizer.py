"""Summarize older memory into compact state."""
from __future__ import annotations

from aiagent.schemas.memory import MemoryItem, MemoryKind


class MemorySummarizer:
    def summarize_user_memories(self, items: list[MemoryItem], limit: int = 10) -> str:
        if not items:
            return "No memory summary available."

        selected = sorted(
            items,
            key=lambda item: (item.importance, item.timestamp),
            reverse=True,
        )[:limit]

        profile_items = [item for item in selected if item.kind == MemoryKind.USER_PORFILE]
        long_term_items = [item for item in selected if item.kind == MemoryKind.LONG_TERM]

        lines: list[str] = []

        if profile_items:
            lines.append("用户画像：")
            for item in profile_items[:4]:
                lines.append(f"- {item.summary or item.content}")

        if long_term_items:
            lines.append("长期事件：")
            for item in long_term_items[:6]:
                lines.append(f"- {item.summary or item.content}")

        return "\n".join(lines) if lines else "No memory summary available."
