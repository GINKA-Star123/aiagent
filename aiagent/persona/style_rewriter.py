"""Rewrite plain responses into persona style."""

from aiagent.schemas.persona import PersonaConfig
from aiagent.services.llm_service import LLMService


class StyleRewriter:
    """Rewrites plain responses into persona style."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def rewrite(self, base_reply:str , persona:PersonaConfig) ->str:
        rewrite_prompt = persona.to_write_prompt()
        return self.llm_service.generate_style_reply(
            system_prompt=rewrite_prompt,
            base_text=base_reply,
            persona_name=persona.name
        )