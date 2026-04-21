"""Rewrite plain responses into persona style."""
from __future__ import annotations

import logging

from aiagent.persona.persona_consistency import PersonaConsistencyGuard
from aiagent.schemas.persona import PersonaConfig
from aiagent.services.llm_service import LLMService


class StyleRewriter:
    """Rewrites plain responses into persona style."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.guard = PersonaConsistencyGuard()
        self.logger = logging.getLogger(self.__class__.__name__)

    def rewrite(self, base_reply: str, persona: PersonaConfig) -> str:
        rewrite_prompt = persona.to_write_prompt()
        rewrite_prompt += (
            "\n额外要求：\n"
            "1. 如果这句话是在承接上一轮话题，改写时不要丢掉核心主题。\n"
            "2. 不要把明确的歌曲名、作品名、人物名改写丢失。\n"
            "3. 只做口吻润色，不要把原本已经接上的上下文改坏。\n"
        )

        messages =self.llm_service.build_messages(
            system_prompt=rewrite_prompt,
            user_text=base_reply,
        )
        try:
            rewritten = self.llm_service.invoke_messages(
                messages=messages,
                fallback_text=base_reply,
                mode="style",
                persona_name=persona.name,
            )
            candidate = rewritten or base_reply
        except Exception as exc:
            self.logger.exception("Style rewrite failed, fallback to base reply: %s", exc)
            candidate = base_reply

        return self.guard.normalize(candidate, persona)
