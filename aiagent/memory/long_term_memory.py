"""Long-term memory interface."""
from __future__ import annotations

import json
from pathlib import Path

from aiagent.schemas.memory import MemoryItem, MemoryKind


class LongTermMemory:
    def __init__(self, file_path: str | Path = "data/memory/long_term_memory.json") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[MemoryItem] = []
        self._load()

    def add_memory(self, item: MemoryItem) -> bool:
        normalized = item.content.strip().lower()

        for existing in self._items:
            if (
                existing.user_id == item.user_id
                and existing.kind == item.kind
                and existing.content.strip().lower() == normalized
            ):
                if item.importance > existing.importance:
                    existing.importance = item.importance
                if item.summary:
                    existing.summary = item.summary
                if item.tags:
                    existing.tags = sorted(set(existing.tags + item.tags))
                if item.confidence > existing.confidence:
                    existing.confidence = item.confidence
                self._save()
                return False

        self._items.append(item)
        self._save()
        return True

    def add_memories(self, items: list[MemoryItem]) -> int:
        stored = 0
        for item in items:
            if self.add_memory(item):
                stored += 1
        return stored

    def recall_for_user(
        self,
        user_id: str,
        limit: int = 8,
        kinds: list[MemoryKind] | None = None,
    ) -> list[MemoryItem]:
        items = [item for item in self._items if item.user_id == user_id]

        if kinds is not None:
            allowed = {kind.value for kind in kinds}
            items = [item for item in items if item.kind.value in allowed]

        items.sort(key=lambda item: (item.importance, item.timestamp), reverse=True)
        return items[:limit]

    def search_for_user(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        query_lower = query.strip().lower()
        if not query_lower:
            return self.recall_for_user(user_id=user_id, limit=limit)

        matched = []
        for item in self._items:
            if item.user_id != user_id:
                continue

            haystack = " ".join(
                [
                    item.content.lower(),
                    item.summary.lower(),
                    " ".join(item.tags).lower(),
                ]
            )
            if query_lower in haystack:
                matched.append(item)

        matched.sort(key=lambda item: (item.importance, item.timestamp), reverse=True)
        return matched[:limit]

    def summarize_for_prompt(self, user_id: str, limit: int = 6) -> str:
        items = self.recall_for_user(user_id=user_id, limit=limit)
        if not items:
            return "No memories found for this user."

        lines = []
        for item in items:
            text = item.summary or item.content
            tag_text = f" [{' ,'.join(item.tags)}]" if item.tags else ""
            lines.append(f"{item.kind.value}: {text}{tag_text}")

        return "\n".join(lines)

    def replace_user_summary(self, user_id: str, username: str, summary_text: str) -> None:
        self._items = [
            item
            for item in self._items
            if not (item.user_id == user_id and item.kind == MemoryKind.SUMMARY)
        ]

        self._items.append(
            MemoryItem(
                user_id=user_id,
                username=username,
                content=summary_text,
                kind=MemoryKind.SUMMARY,
                importance=0.95,
                summary=summary_text,
                source_text=summary_text,
                confidence=0.95,
            )
        )
        self._save()

    def all_for_user(self, user_id: str) -> list[MemoryItem]:
        items = [item for item in self._items if item.user_id == user_id]
        items.sort(key=lambda item: (item.importance, item.timestamp), reverse=True)
        return items

    def stats_for_user(self, user_id: str) -> dict:
        items = self.all_for_user(user_id)
        counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}

        for item in items:
            counts[item.kind.value] = counts.get(item.kind.value, 0) + 1
            for tag in item.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "count": len(items),
            "by_kind": counts,
            "top_tags": [
                tag
                for tag, _count in sorted(tag_counts.items(), key=lambda pair: pair[1], reverse=True)[:8]
            ],
        }

    def clear_user(self, user_id: str) -> None:
        self._items = [item for item in self._items if item.user_id != user_id]
        self._save()

    def _load(self) -> None:
        if not self.file_path.exists():
            self._items = []
            return

        raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        self._items = [MemoryItem(**item) for item in raw]

    def _save(self) -> None:
        payload = [item.model_dump(mode="json") for item in self._items]
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
