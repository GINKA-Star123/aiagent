"""Per-user memory and profile aggregation."""
from __future__ import annotations

from collections import defaultdict

from aiagent.schemas.memory import MemoryItem


class UserProfileMemory:
    def __init__(self) -> None:
        self._profiles: dict[str, list[MemoryItem]] = defaultdict(list)

    def add_memory(self, item: MemoryItem) -> bool:
        existing_items = self._profiles[item.user_id]
        normalized = item.content.strip().lower()

        for existing in existing_items:
            if existing.content.strip().lower() == normalized:
                if item.importance > existing.importance:
                    existing.importance = item.importance
                if item.summary:
                    existing.summary = item.summary
                if item.tags:
                    existing.tags = sorted(set(existing.tags + item.tags))
                return False

        existing_items.append(item)
        existing_items.sort(key=lambda memory: (memory.importance, memory.timestamp), reverse=True)
        self._profiles[item.user_id] = existing_items
        return True

    def add_memories(self, items: list[MemoryItem]) -> int:
        stored = 0
        for item in items:
            if self.add_memory(item):
                stored += 1
        return stored

    def recall_for_user(self, user_id: str, limit: int = 5) -> list[MemoryItem]:
        items = self._profiles.get(user_id, [])
        return items[:limit]

    def all_for_user(self, user_id: str) -> list[MemoryItem]:
        return list(self._profiles.get(user_id, []))

    def search_for_user(self, user_id: str, query: str, limit: int = 10) -> list[MemoryItem]:
        query_lower = query.strip().lower()
        if not query_lower:
            return self.recall_for_user(user_id=user_id, limit=limit)

        matched = []
        for item in self._profiles.get(user_id, []):
            haystack = " ".join(
                [
                    item.content.lower(),
                    item.summary.lower(),
                    " ".join(item.tags).lower(),
                ]
            )
            if query_lower in haystack:
                matched.append(item)

        matched.sort(key=lambda memory: (memory.importance, memory.timestamp), reverse=True)
        return matched[:limit]

    def summarize_for_prompt(self, user_id: str, limit: int = 5) -> str:
        items = self.recall_for_user(user_id, limit)
        if not items:
            return "No memories found for this user."

        lines = []
        for item in items:
            text = item.summary or item.content
            lines.append(f"{item.kind.value}: {text}")

        return "\n".join(lines)

    def stats_for_user(self, user_id: str) -> dict:
        items = self._profiles.get(user_id, [])
        return {
            "count": len(items),
            "top_tags": self._top_tags(items),
        }

    def clear_user(self, user_id: str) -> None:
        self._profiles.pop(user_id, None)

    def _top_tags(self, items: list[MemoryItem]) -> list[str]:
        counts: dict[str, int] = {}
        for item in items:
            for tag in item.tags:
                counts[tag] = counts.get(tag, 0) + 1

        return [
            tag
            for tag, _count in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:8]
        ]
