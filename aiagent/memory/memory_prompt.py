from __future__ import annotations

import re
from typing import Any
from collections import Counter

from aiagent.memory.mem0_memory import MemoryHit
from aiagent.memory.memory_layers import infer_memory_layer
from aiagent.schemas.memory import (
    MemoryCategory,
    MemoryImportance,
    MemoryLayer,
    MemoryPromptContext,
    MemoryPromptItem,
    MemoryPromptSource,
    MemoryRecord,
)

NO_LONG_TERM_MEMORY_TEXT = "无长期记忆。"

IMPORTANCE_RANK: dict[MemoryImportance, int] = {
    MemoryImportance.HIGH: 3,
    MemoryImportance.MEDIUM: 2,
    MemoryImportance.LOW: 1,
}

LAYER_TITLES: dict[MemoryLayer, str] = {
    MemoryLayer.PROFILE: "身份与称呼",
    MemoryLayer.BOUNDARY: "边界与禁忌",
    MemoryLayer.PREFERENCE: "偏好与习惯",
    MemoryLayer.EPISODE: "目标与近期事项",
    MemoryLayer.OTHER: "其他长期记忆",
}

LAYER_PRIORITY = (
    MemoryLayer.PROFILE,
    MemoryLayer.BOUNDARY,
    MemoryLayer.PREFERENCE,
    MemoryLayer.EPISODE,
    MemoryLayer.OTHER,
)

LAYER_LIMITS = {
    MemoryLayer.PROFILE: 2,
    MemoryLayer.BOUNDARY: 1,
    MemoryLayer.PREFERENCE: 2,
    MemoryLayer.EPISODE: 1,
    MemoryLayer.OTHER: 1,
}


class MemoryPromptBuilder:
    def __init__(
        self,
        *,
        max_chars: int = 1200,
        pinned_limit: int = 4,
        relevant_limit: int = 6,
        item_max_chars: int = 120,
    ) -> None:
        self.max_chars = max(max_chars, 300)
        self.pinned_limit = max(pinned_limit, 0)
        self.relevant_limit = max(relevant_limit, 0)
        self.item_max_chars = max(item_max_chars, 40)

    def build(
        self,
        *,
        hits: list[MemoryHit],
        pinned_records: list[MemoryRecord] | None = None,
    ) -> MemoryPromptContext:
        pinned_items = [
            self._item_from_record(record)
            for record in (pinned_records or [])
            if record.memory.strip() and record.pinned
        ]

        hit_items = [
            self._item_from_hit(hit)
            for hit in hits
            if hit.memory.strip()
        ]

        selected = self._select_items(
            pinned_items=pinned_items,
            hit_items=hit_items,
        )

        if not selected:
            return MemoryPromptContext(
                text=NO_LONG_TERM_MEMORY_TEXT,
                items=[],
                total_count=0,
                pinned_count=0,
                retrieved_count=0,
                char_count=len(NO_LONG_TERM_MEMORY_TEXT),
                max_chars=self.max_chars,
                truncated=False,
            )

        text, truncated = self._render(selected)
        layer_counts = Counter(item.layer.value for item in selected)
        return MemoryPromptContext(
            text=text,
            items=selected,
            total_count=len(selected),
            pinned_count=sum(1 for item in selected if item.source == MemoryPromptSource.PINNED),
            retrieved_count=sum(1 for item in selected if item.source == MemoryPromptSource.RETRIEVED),
            char_count=len(text),
            max_chars=self.max_chars,
            truncated=truncated,
            layer_counts=layer_counts,
            selected_ids=[item.id for item in selected if item.id],
            selected_layers=[item.layer.value for item in selected],
            compression_reason="char_limit" if truncated else "layered_compact",
        )

    def _select_items(
        self,
        *,
        pinned_items: list[MemoryPromptItem],
        hit_items: list[MemoryPromptItem],
    ) -> list[MemoryPromptItem]:
        deduped_pinned = self._dedupe_items(
            sorted(pinned_items, key=self._item_rank, reverse=True)
        )[: self.pinned_limit]

        pinned_ids = {item.id for item in deduped_pinned if item.id}
        pinned_texts = {self._normalize_text(item.memory) for item in deduped_pinned}

        relevant_candidates = []
        for item in hit_items:
            if item.id and item.id in pinned_ids:
                continue
            if self._normalize_text(item.memory) in pinned_texts:
                continue
            relevant_candidates.append(item)

        deduped_relevant = self._dedupe_items(
            sorted(relevant_candidates, key=self._item_rank, reverse=True)
        )[: self.relevant_limit]

        return [*deduped_pinned, *deduped_relevant]

    def _render(self, items: list[MemoryPromptItem]) -> tuple[str, bool]:
        lines: list[str] = [
            "长期记忆摘要：",
            "- 这些记忆只用于保持称呼、偏好、边界和长期上下文一致。",
            "- 置顶记忆优先级最高，但如果与用户当前表达冲突，以用户当前表达为准。",
            "- 不要告诉用户“我从记忆里看到”，也不要机械复述记忆。",
        ]

        pinned = [item for item in items if item.source == MemoryPromptSource.PINNED]
        retrieved = [item for item in items if item.source == MemoryPromptSource.RETRIEVED]

        if pinned:
            lines.append("")
            lines.append("【置顶记忆】")
            lines.extend(self._numbered_lines(pinned))

        for layer in [
            MemoryLayer.PROFILE,
            MemoryLayer.BOUNDARY,
            MemoryLayer.PREFERENCE,
            MemoryLayer.EPISODE,
            MemoryLayer.OTHER,
        ]:
            layer_items = [item for item in retrieved if item.layer == layer]
            if not layer_items:
                continue

            lines.append("")
            lines.append(f"【{LAYER_TITLES[layer]}】")
            lines.extend(self._numbered_lines(layer_items))

        return self._truncate_lines(lines)

    def _numbered_lines(self, items: list[MemoryPromptItem]) -> list[str]:
        result: list[str] = []
        for index, item in enumerate(items, start=1):
            label = self._label(item)
            text = self._compact_text(item.memory)
            result.append(f"{index}. {text}{label}")
        return result

    def _label(self, item: MemoryPromptItem) -> str:
        parts = []
        if item.importance == MemoryImportance.HIGH:
            parts.append("高重要度")
        if item.category != MemoryCategory.OTHER:
            parts.append(item.category.value)
        if not parts:
            return ""
        return f"（{ ' / '.join(parts) }）"

    def _truncate_lines(self, lines: list[str]) -> tuple[str, bool]:
        kept: list[str] = []
        used = 0
        truncated = False

        for line in lines:
            next_used = used + len(line) + 1
            if next_used > self.max_chars:
                truncated = True
                break
            kept.append(line)
            used = next_used

        if truncated:
            suffix = "【提示】长期记忆已压缩截断，仅展示最高优先级内容。"
            if used + len(suffix) + 1 <= self.max_chars:
                kept.append("")
                kept.append(suffix)

        text = "\n".join(kept).strip()
        return text or NO_LONG_TERM_MEMORY_TEXT, truncated

    def _item_from_record(self, record: MemoryRecord) -> MemoryPromptItem:
        metadata = dict(record.metadata or {})
        return MemoryPromptItem(
            id=record.id,
            memory=self._compact_text(record.memory),
            source=MemoryPromptSource.PINNED,
            layer=record.layer,
            category=record.category,
            importance=record.importance,
            score=record.score,
            pinned=True,
            reason="user_pinned_memory",
            metadata=metadata,
        )

    def _item_from_hit(self, hit: MemoryHit) -> MemoryPromptItem:
        metadata = hit.metadata if isinstance(hit.metadata, dict) else {}
        category = self._enum_value(
            MemoryCategory,
            metadata.get("category") or metadata.get("memory_category"),
            MemoryCategory.OTHER,
        )
        importance = self._enum_value(
            MemoryImportance,
            metadata.get("importance") or metadata.get("memory_importance"),
            MemoryImportance.MEDIUM,
        )
        layer = infer_memory_layer(category, metadata)

        return MemoryPromptItem(
            id=hit.id,
            memory=self._compact_text(hit.memory),
            source=MemoryPromptSource.PINNED if hit.pinned else MemoryPromptSource.RETRIEVED,
            layer=layer,
            category=category,
            importance=importance,
            score=hit.score,
            pinned=hit.pinned,
            reason="retrieved_memory",
            metadata=dict(metadata),
        )

    def _dedupe_items(self, items: list[MemoryPromptItem]) -> list[MemoryPromptItem]:
        seen_ids: set[str] = set()
        seen_texts: set[str] = set()
        result: list[MemoryPromptItem] = []

        for item in items:
            normalized = self._normalize_text(item.memory)
            if item.id and item.id in seen_ids:
                continue
            if normalized in seen_texts:
                continue

            if item.id:
                seen_ids.add(item.id)
            seen_texts.add(normalized)
            result.append(item)

        return result

    def _item_rank(self, item: MemoryPromptItem) -> tuple[int, int, float, int]:
        return (
            1 if item.pinned else 0,
            IMPORTANCE_RANK.get(item.importance, 0),
            float(item.score or 0.0),
            len(item.memory),
        )

    def _compact_text(self, text: str) -> str:
        compact = re.sub(r"\s+", " ", (text or "").strip())
        compact = compact.replace("；", "；")
        if len(compact) <= self.item_max_chars:
            return compact
        return compact[: self.item_max_chars - 1].rstrip() + "…"

    def _normalize_text(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        normalized = re.sub(r"\s+", "", normalized)
        normalized = re.sub(r"[，。！？、,.!?;；：:（）()\[\]【】\"'“”‘’]", "", normalized)
        return normalized

    def _enum_value(self, enum_cls, value: Any, fallback):
        try:
            return enum_cls(str(value))
        except Exception:
            return fallback