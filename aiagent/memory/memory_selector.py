"""Select and extract memories from input/output events."""
from __future__ import annotations

import re

from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.memory import MemoryItem, MemoryKind
from aiagent.schemas.outputs import OutputEvent


class MemorySelector:
    PROFILE_KEYWORDS = [
        "我叫",
        "我是",
        "我喜欢",
        "我讨厌",
        "我最近",
        "我今天",
        "我明天",
        "请记住",
        "记住我",
    ]

    LONG_TERM_KEYWORDS = [
        "考试",
        "生日",
        "工作",
        "学校",
        "毕业",
        "分手",
        "家人",
        "生病",
        "目标",
        "梦想",
        "计划",
        "重要",
        "以后",
        "一直",
    ]

    TAG_PATTERNS = {
        "exam": ["考试", "复习", "成绩"],
        "music": ["唱歌", "音乐", "吉他", "钢琴", "作曲"],
        "emotion": ["紧张", "开心", "难过", "焦虑", "压力"],
        "school": ["学校", "老师", "同学", "大学", "上课"],
        "work": ["工作", "上班", "同事", "老板", "加班"],
        "birthday": ["生日"],
    }

    def should_store_user_profile(self, event: InputEvent) -> bool:
        return any(keyword in event.text for keyword in self.PROFILE_KEYWORDS)

    def should_store_long_term_memory(self, event: InputEvent, output: OutputEvent | None = None) -> bool:
        if any(keyword in event.text for keyword in self.LONG_TERM_KEYWORDS):
            return True

        if len(event.text.strip()) >= 24:
            return True

        if output is not None and output.packet.should_store_memory:
            return True

        return False

    def extract_profile_memories(self, event: InputEvent) -> list[MemoryItem]:
        if not self.should_store_user_profile(event):
            return []

        tags = self._extract_tags(event.text)
        summary = self._build_summary(event.text, max_len=36)

        return [
            MemoryItem(
                user_id=event.user_id,
                username=event.user_name,
                content=event.text.strip(),
                kind=MemoryKind.USER_PORFILE,
                importance=0.78,
                tags=tags,
                summary=summary,
                source_text=event.text.strip(),
                confidence=0.82,
            )
        ]

    def extract_long_term_memories(
        self,
        event: InputEvent,
        output: OutputEvent | None = None,
    ) -> list[MemoryItem]:
        if not self.should_store_long_term_memory(event, output):
            return []

        importance = self._score_importance(event.text, output)
        tags = self._extract_tags(event.text)
        summary = self._build_summary(event.text, max_len=40)

        return [
            MemoryItem(
                user_id=event.user_id,
                username=event.user_name,
                content=event.text.strip(),
                kind=MemoryKind.LONG_TERM,
                importance=importance,
                tags=tags,
                summary=summary,
                source_text=event.text.strip(),
                confidence=0.75 if importance < 0.85 else 0.9,
            )
        ]

    def _score_importance(self, text: str, output: OutputEvent | None = None) -> float:
        score = 0.65
        stripped = text.strip()

        if len(stripped) >= 20:
            score += 0.08
        if len(stripped) >= 40:
            score += 0.05
        if any(keyword in stripped for keyword in self.LONG_TERM_KEYWORDS):
            score += 0.12
        if "请记住" in stripped or "记住" in stripped:
            score += 0.08
        if output is not None and output.packet.should_store_memory:
            score += 0.1

        return min(score, 0.98)

    def _extract_tags(self, text: str) -> list[str]:
        tags: list[str] = []
        for tag, keywords in self.TAG_PATTERNS.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)

        custom_terms = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        for term in custom_terms[:3]:
            if term not in tags and len(tags) < 6:
                tags.append(term)

        return tags

    def _build_summary(self, text: str, max_len: int = 40) -> str:
        normalized = re.sub(r"\s+", " ", text.strip())
        if len(normalized) <= max_len:
            return normalized
        return normalized[: max_len - 1] + "…"
