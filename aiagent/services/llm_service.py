from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.providers import LLMProvider
from config.settings import Settings


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self._chat_model: BaseChatModel | None = None

    def _resolve_provider_config(self) -> tuple[str | None, str, str]:
        if self.settings.llm_provider == LLMProvider.OPENAI:
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured.")
            return (
                self.settings.openai_api_key,
                self.settings.openai_base_url,
                "OpenAI",
            )

        if self.settings.llm_provider == LLMProvider.SILICONFLOW:
            if not self.settings.siliconflow_api_key:
                raise RuntimeError("SILICONFLOW_API is not configured.")
            return (
                self.settings.siliconflow_api_key,
                self.settings.siliconflow_base_url,
                "SiliconFlow",
            )

        if self.settings.llm_provider == LLMProvider.LMSTUDIO:
            return (
                self.settings.lmstudio_api_key or "lm-studio",
                self.settings.lmstudio_base_url,
                "LM Studio",
            )

        raise ValueError(f"Unsupported llm provider: {self.settings.llm_provider}")

    def get_chat_model(self) -> BaseChatModel:
        if self._chat_model is not None:
            return self._chat_model

        api_key, base_url, provider_name = self._resolve_provider_config()
        self.logger.info("Using %s provider", provider_name)

        self._chat_model = ChatOpenAI(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            timeout=self.settings.llm_timeout_seconds,
            api_key=api_key,  # type: ignore[arg-type]
            base_url=base_url,
            max_completion_tokens=self.settings.llm_max_tokens,
        )
        return self._chat_model

    def build_messages(
        self,
        system_prompt: str,
        user_text: str,
        history_messages: Sequence[BaseMessage] | None = None,
    ) -> list[BaseMessage]:
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        if history_messages:
            messages.extend(history_messages)
        messages.append(HumanMessage(content=user_text))
        return messages

    def invoke_messages(
        self,
        messages: Sequence[BaseMessage],
        fallback_text: str,
        mode: str = "chat",
        persona_name: str | None = None,
    ) -> str:
        del mode, persona_name

        if self.settings.enable_mock_llm or self.settings.llm_provider == LLMProvider.MOCK:
            return fallback_text

        try:
            return self.invoke_messages_strict(messages)
        except Exception as exc:
            self.logger.exception("LLM invoke failed: %s", exc)
            return fallback_text

    def invoke_with_memory(
        self,
        thread_id: str,
        system_prompt: str,
        user_text: str,
        fallback_text: str,
        mode: str = "chat",
        persona_name: str | None = None,
    ) -> str:
        del thread_id
        messages = self.build_messages(
            system_prompt=system_prompt,
            user_text=user_text,
        )
        return self.invoke_messages(
            messages=messages,
            fallback_text=fallback_text,
            mode=mode,
            persona_name=persona_name,
        )

    def invoke_messages_strict(self, messages: Sequence[BaseMessage]) -> str:
        if self.settings.enable_mock_llm or self.settings.llm_provider == LLMProvider.MOCK:
            raise RuntimeError("strict invocation does not allow mock LLM")
        if self.settings.llm_provider == LLMProvider.LMSTUDIO:
            content = self._invoke_lmstudio(messages)
        else:
            response = self.get_chat_model().invoke(list(messages))
            raw = getattr(response,"content",response)
            if not isinstance(raw,(str,list)):
                raise TypeError("LLM returneda unsupported content type")
            content = self._normalize_content(raw)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LLM returned empty content.")
        return content.strip()

    def _invoke_lmstudio(self, messages: Sequence[BaseMessage]) -> str:
        _, base_url, _ = self._resolve_provider_config()

        payload = {
            "model": self.settings.llm_model,
            "messages": [self._to_openai_message(message) for message in messages],
            "temperature": self.settings.llm_temperature,
        }

        with httpx.Client(timeout=self.settings.llm_timeout_seconds, trust_env=False) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.settings.lmstudio_api_key or 'lm-studio'}",
                },
            )

        if response.is_error:
            raise RuntimeError(
                f"LM Studio request failed: {response.status_code} {response.text}"
            )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"LM Studio returned no choices: {data}")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        normalized = self._normalize_content(content)
        if not normalized:
            raise RuntimeError(f"LM Studio returned empty content: {data}")

        return normalized

    def _to_openai_message(self, message: BaseMessage) -> dict[str, str]:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = "user"

        return {
            "role": role,
            "content": self._normalize_content(message.content),
        }

    def _normalize_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()

        return str(content).strip()
