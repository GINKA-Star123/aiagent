"""Persona consistency post-processing."""
from __future__ import annotations

import re

from aiagent.schemas.persona import PersonaConfig


class PersonaConsistencyGuard:
    BANNED_PATTERNS = [
        r"^我是[^，。！？]{1,12}[，。！？]?",
        r"^这里是[^，。！？]{1,12}[，。！？]?",
        r"^这边先[^，。！？]{1,20}[，。！？]?",
        r"^收到啦[，。！？]?",
        r"^我先接住这条消息[，。！？]?",
        r"^作为一个AI[^，。！？]*",
        r"^作为AI[^，。！？]*",
        r"^作为助手[^，。！？]*",
    ]

    OVER_FORMAL_PATTERNS = [
        (r"我将为你", "我来"),
        (r"建议你可以", "你可以"),
        (r"如果你愿意的话", "如果你愿意"),
        (r"从这个角度来说", "这样看"),
        (r"根据你的描述", "听你这么说"),
    ]

    def normalize(self, text: str, persona: PersonaConfig) -> str:
        cleaned = text.strip()

        for pattern in self.BANNED_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned).strip()

        for source, target in self.OVER_FORMAL_PATTERNS:
            cleaned = re.sub(source, target, cleaned)

        cleaned = self._remove_repeated_intro(cleaned)
        cleaned = self._trim_overlong(cleaned)
        cleaned = self._soften_robotic_tail(cleaned)
        cleaned = self._normalize_punctuation(cleaned)

        return cleaned.strip() or self._fallback_reply(persona)

    def _remove_repeated_intro(self, text: str) -> str:
        prefixes = [
            "嗯，",
            "嗯嗯，",
            "那个，",
            "就是说，",
            "怎么说呢，",
        ]
        for prefix in prefixes:
            if text.startswith(prefix) and len(text) > len(prefix) + 6:
                return text[len(prefix):].strip()
        return text

    def _trim_overlong(self, text: str) -> str:
        if len(text) <= 88:
            return text

        sentences = re.split(r"(?<=[。！？])", text)
        collected = ""
        for sentence in sentences:
            candidate = (collected + sentence).strip()
            if len(candidate) > 88 and collected:
                break
            collected = candidate

        return collected.strip() if collected else text[:88].strip()

    def _soften_robotic_tail(self, text: str) -> str:
        endings = [
            "希望这能帮到你。",
            "希望可以帮助到你。",
            "如果你愿意我还可以继续帮你。",
            "如有需要可以继续告诉我。",
        ]
        for ending in endings:
            if text.endswith(ending):
                text = text[: -len(ending)].rstrip()
        return text

    def _normalize_punctuation(self, text: str) -> str:
        text = text.replace("。。", "。")
        text = text.replace("！！", "！")
        text = text.replace("？？", "？")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _fallback_reply(self, persona: PersonaConfig) -> str:
        if persona.name == "乐正绫":
            return "这句我先接住啦，你继续说。"
        return "我在，继续说吧。"
