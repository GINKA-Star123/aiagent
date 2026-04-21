"""LLM service with LangGraph checkpointer memory."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import MessagesState, START, StateGraph

from config.providers import LLMProvider
from config.settings import Settings


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self._chat_model: BaseChatModel | None = None
        self._checkpointer = InMemorySaver()
        self._graph = self._build_graph()

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
        )
        return self._chat_model

    def _build_graph(self):
        builder = StateGraph(MessagesState)
        builder.add_node("store_user_message", self._store_user_message_node)
        builder.add_edge(START, "store_user_message")
        return builder.compile(checkpointer=self._checkpointer)

    def _store_user_message_node(self, state: MessagesState) -> dict[str, list[BaseMessage]]:
        return {"messages": state["messages"]}

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
        mode: str,
        persona_name: str | None = None,
    ) -> str:
        if self.settings.enable_mock_llm or self.settings.llm_provider == LLMProvider.MOCK:
            return fallback_text

        try:
            if self.settings.llm_provider == LLMProvider.LMSTUDIO:
                content = self._invoke_lmstudio(messages)
            else:
                response = self.get_chat_model().invoke(list(messages))
                content = self._normalize_content(getattr(response, "content", response))
            return content or fallback_text
        except Exception as exc:
            self.logger.exception("LLM invoke failed: %s", exc)
            if mode == "style":
                return fallback_text
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
        del mode, persona_name

        if self.settings.enable_mock_llm or self.settings.llm_provider == LLMProvider.MOCK:
            return fallback_text

        config = {"configurable": {"thread_id": thread_id}}

        try:
            self._graph.invoke(
                {
                    "messages": [HumanMessage(content=user_text)],
                },
                config=config,
            )

            history_messages = self.recent_messages(thread_id=thread_id, limit_turns=4)
            prompt_messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
            prompt_messages.extend(history_messages)

            self.logger.info(
                "Invoking LM with %s messages: %s",
                len(prompt_messages),
                [type(msg).__name__ for msg in prompt_messages],
            )

            if self.settings.llm_provider == LLMProvider.LMSTUDIO:
                reply_text = self._invoke_lmstudio(prompt_messages)
            else:
                response = self.get_chat_model().invoke(prompt_messages)
                reply_text = self._normalize_content(getattr(response, "content", response))

            self._graph.invoke(
                {
                    "messages": [AIMessage(content=reply_text)],
                },
                config=config,
            )

            return reply_text or fallback_text

        except Exception as exc:
            self.logger.exception("LLM graph invoke failed: %s", exc)
            return fallback_text

    def recent_messages(
        self,
        thread_id: str,
        limit_turns: int = 4,
        exclude_input_text: str | None = None,
    ) -> list[BaseMessage]:
        state = self._get_state(thread_id)
        messages = list(state.get("messages", []))

        if exclude_input_text and messages and isinstance(messages[-1], HumanMessage):
            last_text = self._normalize_content(messages[-1].content)
            if last_text == exclude_input_text.strip():
                messages = messages[:-1]

        max_messages = max(limit_turns * 2, 0)
        return messages[-max_messages:] if max_messages else []

    def recent_dialogue_lines(self, thread_id: str, limit: int = 6) -> list[str]:
        messages = self.recent_messages(thread_id=thread_id, limit_turns=max(limit // 2, 1))
        lines: list[str] = []

        for message in messages:
            if isinstance(message, HumanMessage):
                role = "用户"
            elif isinstance(message, AIMessage):
                role = "助手"
            else:
                role = getattr(message, "type", "unknown")

            text = self._normalize_content(message.content)
            if text:
                lines.append(f"{role}: {text}")

        return lines[-limit:]

    def clear_short_term(self, thread_id: str | None = None) -> None:
        if thread_id is None:
            self._checkpointer = InMemorySaver()
            self._graph = self._build_graph()
            return

        self._graph.update_state(
            {"configurable": {"thread_id": thread_id}},
            {"messages": []},
        )

    def _get_state(self, thread_id: str) -> dict[str, Any]:
        snapshot = self._graph.get_state({"configurable": {"thread_id": thread_id}})
        values = getattr(snapshot, "values", {})
        return values if isinstance(values, dict) else {}

    def _invoke_lmstudio(self, messages: Sequence[BaseMessage]) -> str:
        _, base_url, _ = self._resolve_provider_config()
        payload = {
            "model": self.settings.llm_model,
            "messages": [self._to_openai_message(message) for message in messages],
            "temperature": self.settings.llm_temperature,
        }

        self.logger.info(
            "Calling LM Studio with %s messages and model=%s",
            len(payload["messages"]),
            self.settings.llm_model,
        )

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
