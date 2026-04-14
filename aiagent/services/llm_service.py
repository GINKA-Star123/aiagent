"""LLM service facade."""

import logging

from config.providers import LLMProvider
from config.settings import Settings
from integrations.llm.openai_client import OpenAIClient
from integrations.llm.prompt_adapter import build_messages
from integrations.llm.siliconflow_client import SiliconFlowClient


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

        self.openai_client = OpenAIClient(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        self.siliconflow_client = SiliconFlowClient(
            api_key=settings.siliconflow_api_key,
            model=settings.llm_model,
            base_url=settings.siliconflow_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    def generate_reply(self, system_prompt: str, user_text: str) -> str:
        messages = build_messages(system_prompt, user_text)
        return self._generate(messages=messages, mock_text=user_text, mode="reply")

    def generate_style_reply(self, system_prompt: str, base_text: str, persona_name: str) -> str:
        messages = build_messages(system_prompt, base_text)
        return self._generate(
            messages=messages,
            mock_text=base_text,
            mode="style",
            persona_name=persona_name,
        )

    def _generate(self, messages, mock_text: str, mode: str, persona_name: str | None = None) -> str:
        if self.settings.enable_mock_llm or self.settings.llm_provider == LLMProvider.MOCK:
            self.logger.info("Using mock LLM mode.")
            return self._mock_response(mock_text, mode=mode, persona_name=persona_name)

        try:
            if self.settings.llm_provider == LLMProvider.OPENAI:
                self.logger.info("Using OpenAI provider.")
                return self.openai_client.generate(messages)

            if self.settings.llm_provider == LLMProvider.SILICONFLOW:
                self.logger.info("Using SiliconFlow provider.")
                return self.siliconflow_client.generate(messages)

            raise ValueError(f"Unsupported llm provider: {self.settings.llm_provider}")

        except Exception as exc:
            self.logger.exception("LLM provider call failed, falling back to mock response: %s", exc)
            return self._mock_response(mock_text, mode=mode, persona_name=persona_name)

    def _mock_response(self, text: str, mode: str, persona_name: str | None = None) -> str:
        if mode == "style":
            return f"{text} 我是{persona_name or '乐正绫'}，这边先轻松接住这句。"
        return f"收到啦，你刚刚说的是：{text}。我先接住这条消息。"
