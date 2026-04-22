from __future__ import annotations

import re

from aiagent.persona.persona_models import PersonaConfig


class PersonaGuard:
    def normalize_reply(self,text:str) ->str:
        cleaned = text.strip()

        cleaned = cleaned.replace("\r", " ").replace("\n", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)

        cleaned = re.sub(r"^[，。！？、\s]+", "", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)

        return cleaned.strip() or "嗯，我在听。"
    
    def validate_reply(self,text:str,persona:PersonaConfig) -> list[str]:
        issues:list[str] = []
        lowered = text.lower()

        if "我是ai" in lowered:
            issues.append("回复包含关键词：我是ai")

        for phrase in persona.style.avoid_phrase:
            if phrase and phrase in lowered:
                issues.append(f"回复包含禁用词：{phrase}")

        return issues