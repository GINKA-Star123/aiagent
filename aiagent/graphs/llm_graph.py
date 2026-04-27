from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langmem.short_term import RunningSummary, SummarizationNode

from aiagent.graphs.graph_model import LLMGraphInput, LLMGraphResult
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.services.llm_service import LLMService
from config.providers import LLMProvider


class LLMGraphState(MessagesState):
    context: dict[str, RunningSummary]
    summarized_messages: list[AnyMessage]
    input: dict[str, Any]
    final_system_prompt: str
    prompt_messages: list[BaseMessage]
    raw_reply_text: str
    final_reply_text: str
    validation_issues: list[str]
    metadata: dict[str, str]


class LLMRunner:
    def __init__(
        self,
        llm_service: LLMService,
        short_term_turn_window: int = 6,
    ) -> None:
        self.llm_service = llm_service
        self.short_term_turn_window = short_term_turn_window
        self.checkpointer = InMemorySaver()
        self._persona_runtime_cache: dict[str, PersonaRuntime] = {}
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LLMGraphState)
        summarize_node = self._create_summarize_node()

        graph.add_node("summarize", summarize_node)
        graph.add_node("build_prompt", self._build_prompt_node)
        graph.add_node("call_llm", self._call_llm_node)
        graph.add_node("normalize_reply", self._normalize_reply_node)

        graph.add_edge(START, "summarize")
        graph.add_edge("summarize", "build_prompt")
        graph.add_edge("build_prompt", "call_llm")
        graph.add_edge("call_llm", "normalize_reply")
        graph.add_edge("normalize_reply", END)

        return graph.compile(checkpointer=self.checkpointer)

    def _create_summarize_node(self):
        if (
            self.llm_service.settings.enable_mock_llm
            or self.llm_service.settings.llm_provider == LLMProvider.MOCK
        ):
            return self._mock_summarize_node

        summary_model = self.llm_service.get_chat_model().bind(max_tokens=128)

        return SummarizationNode(
            token_counter=count_tokens_approximately,
            model=summary_model,
            max_tokens=1024,
            max_tokens_before_summary=768,
            max_summary_tokens=256,
        )

    def _mock_summarize_node(self, state: LLMGraphState) -> dict[str, object]:
        messages = list(state.get("messages", []))
        return {
            "summarized_messages": messages[-(self.short_term_turn_window * 2):],
            "context": state.get("context", {}),
        }

    def _build_prompt_node(self, state: LLMGraphState) -> dict[str, object]:
        graph_input = self._state_input(state)
        persona_runtime = self._get_persona_runtime(graph_input.thread_id)

        summarized_messages = list(state.get("summarized_messages", []))
        if not summarized_messages:
            summarized_messages = self._slice_short_term_messages(list(state.get("messages", [])))

        final_system_prompt = self._build_final_system_prompt(
            graph_input=graph_input,
            persona_runtime=persona_runtime,
            summary_context=state.get("context", {}),
        )

        prompt_messages: list[BaseMessage] = [SystemMessage(content=final_system_prompt)]
        prompt_messages.extend(summarized_messages)

        return {
            "final_system_prompt": final_system_prompt,
            "prompt_messages": prompt_messages,
            "metadata": {
                "llm_prompt": "built",
                "short_term_window": str(self.short_term_turn_window),
                "history_message_count": str(len(summarized_messages)),
                "summary_enabled": "true",
                "retrieved_context_count": str(len(graph_input.retrieved_context)),
            },
        }

    def _call_llm_node(self, state: LLMGraphState) -> dict[str, object]:
        graph_input = self._state_input(state)
        prompt_messages = state["prompt_messages"]

        raw_reply_text = self.llm_service.invoke_messages(
            messages=prompt_messages,
            fallback_text=graph_input.user_text,
            mode="chat",
            persona_name=graph_input.persona_alias or graph_input.persona_name,
        )

        metadata = dict(state.get("metadata", {}))
        metadata["llm_inference"] = "model"

        return {
            "messages": [AIMessage(content=raw_reply_text)],
            "raw_reply_text": raw_reply_text,
            "metadata": metadata,
        }

    def _normalize_reply_node(self, state: LLMGraphState) -> dict[str, object]:
        graph_input = self._state_input(state)
        persona_runtime = self._get_persona_runtime(graph_input.thread_id)
        raw_reply_text = state["raw_reply_text"]

        final_reply_text = persona_runtime.normalize_reply(raw_reply_text)
        validation_issues = persona_runtime.validate_reply(final_reply_text)

        metadata = dict(state.get("metadata", {}))
        metadata["reply_normalization"] = "persona_guard"

        return {
            "final_reply_text": final_reply_text,
            "validation_issues": validation_issues,
            "metadata": metadata,
        }

    def run(
        self,
        thread_id: str,
        user_text: str,
        user_name: str,
        state_result: Any,
        planner_result: Any,
        persona_runtime: PersonaRuntime,
        retrieved_context: list[str] | None = None,
    ) -> LLMGraphResult:
        self._persona_runtime_cache[thread_id] = persona_runtime

        graph_input = LLMGraphInput(
            thread_id=thread_id,
            user_text=user_text,
            user_name=user_name,
            persona_id=persona_runtime.persona_id,
            persona_name=persona_runtime.name,
            persona_alias=persona_runtime.alias,
            state_emotion=state_result.emotion,
            state_intent=state_result.intent,
            state_topic=state_result.topic,
            state_motion_hint=state_result.motion_hint,
            state_context_summary=state_result.context_summary,
            state_confidence=state_result.confidence,
            state_reasoning=state_result.reasoning,
            strategy=planner_result.strategy,
            should_store_memory=planner_result.should_store_memory,
            should_speak=planner_result.should_speak,
            target_emotion=planner_result.target_emotion,
            target_motion=planner_result.target_motion,
            target_expression=planner_result.target_expression,
            reply_instruction=planner_result.reply_instruction,
            planner_reasoning=planner_result.reasoning,
            planner_confidence=planner_result.confidence,
            retrieved_context=retrieved_context or [],
        )

        result = self.graph.invoke( 
            {
                "input": graph_input.model_dump(mode="json"), # type: ignore
                "messages": [HumanMessage(content=user_text)],
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        return LLMGraphResult(
            thread_id=graph_input.thread_id,
            user_text=graph_input.user_text,
            user_name=graph_input.user_name,
            persona_id=graph_input.persona_id,
            persona_name=graph_input.persona_name,
            persona_alias=graph_input.persona_alias,
            reply_text=result["final_reply_text"],
            validation_issues=result.get("validation_issues", []),
            should_store_memory=graph_input.should_store_memory,
            should_speak=graph_input.should_speak,
            target_emotion=graph_input.target_emotion or persona_runtime.get_default_emotion(),
            target_motion=graph_input.target_motion or persona_runtime.get_default_motion(),
            target_expression=graph_input.target_expression or persona_runtime.get_default_expression(),
            short_term_messages=self.recent_dialogue_lines(thread_id=thread_id, limit=8),
            retrieved_context=graph_input.retrieved_context,
            metadata=result.get("metadata", {}),
        )

    def recent_dialogue_lines(self, thread_id: str, limit: int = 8) -> list[str]:
        snapshot = self.graph.get_state({"configurable": {"thread_id": thread_id}})
        if snapshot is None:
            return []

        values = getattr(snapshot, "values", {})
        if not isinstance(values, dict):
            return []

        lines: list[str] = []

        context = values.get("context", {})
        if isinstance(context, dict):
            running_summary = context.get("running_summary")
            summary_text = getattr(running_summary, "summary", "") if running_summary else ""
            if isinstance(summary_text, str) and summary_text.strip():
                lines.append(f"历史摘要: {summary_text.strip()}")

        messages = values.get("messages", [])
        for message in messages:
            if isinstance(message, SystemMessage):
                continue

            role = self._message_role_name(message)
            text = self._message_text(message)
            if text:
                lines.append(f"{role}: {text}")

        return lines[-limit:]

    def clear_thread(self, thread_id: str) -> None:
        self._persona_runtime_cache.pop(thread_id, None)
        self.graph.update_state(
            {"configurable": {"thread_id": thread_id}},
            {
                "messages": [],
                "context": {},
                "summarized_messages": [],
            },
        )

    def clear_all_threads(self) -> None:
        self._persona_runtime_cache.clear()
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _state_input(self, state: LLMGraphState) -> LLMGraphInput:
        raw_input = state["input"]
        if isinstance(raw_input, LLMGraphInput):
            return raw_input
        return LLMGraphInput(**raw_input)

    def _get_persona_runtime(self, thread_id: str) -> PersonaRuntime:
        persona_runtime = self._persona_runtime_cache.get(thread_id)
        if persona_runtime is None:
            raise RuntimeError(f"PersonaRuntime not found for thread_id: {thread_id}")
        return persona_runtime

    def _slice_short_term_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        filtered = [message for message in messages if not isinstance(message, SystemMessage)]
        max_messages = max(self.short_term_turn_window * 2, 0)
        if max_messages <= 0:
            return []
        return filtered[-max_messages:]

    def _build_final_system_prompt(
        self,
        graph_input: LLMGraphInput,
        persona_runtime: PersonaRuntime,
        summary_context: dict[str, RunningSummary],
    ) -> str:
        retrieved_context_text = (
            "\n\n".join(graph_input.retrieved_context)
            if graph_input.retrieved_context
            else "无"
        )

        running_summary = summary_context.get("running_summary")
        short_term_summary = getattr(running_summary, "summary", "") if running_summary else ""
        if not isinstance(short_term_summary, str) or not short_term_summary.strip():
            short_term_summary = "无"

        return (
            f"{persona_runtime.build_system_prompt()}\n\n"
            f"当前用户信息:\n"
            f"- user_name: {graph_input.user_name}\n"
            f"- persona_name: {graph_input.persona_name}\n"
            f"- persona_alias: {graph_input.persona_alias or graph_input.persona_name}\n\n"
            f"短期记忆摘要:\n{short_term_summary}\n\n"
            f"状态分析结果:\n"
            f"- emotion: {graph_input.state_emotion}\n"
            f"- intent: {graph_input.state_intent}\n"
            f"- topic: {graph_input.state_topic}\n"
            f"- motion_hint: {graph_input.state_motion_hint}\n"
            f"- context_summary: {graph_input.state_context_summary}\n"
            f"- state_confidence: {graph_input.state_confidence}\n"
            f"- state_reasoning: {graph_input.state_reasoning}\n\n"
            f"回复规划结果:\n"
            f"- strategy: {graph_input.strategy}\n"
            f"- should_store_memory: {graph_input.should_store_memory}\n"
            f"- should_speak: {graph_input.should_speak}\n"
            f"- target_emotion: {graph_input.target_emotion}\n"
            f"- target_motion: {graph_input.target_motion}\n"
            f"- target_expression: {graph_input.target_expression}\n"
            f"- planner_confidence: {graph_input.planner_confidence}\n"
            f"- planner_reasoning: {graph_input.planner_reasoning}\n"
            f"- reply_instruction: {graph_input.reply_instruction}\n\n"
            f"外部知识库上下文:\n{retrieved_context_text}\n\n"
            f"最终生成要求:\n"
            f"1. 直接输出最终回复，不要解释分析过程。\n"
            f"2. 不要输出 JSON，不要写思考过程。\n"
            f"3. 不要重新自我介绍。\n"
            f"4. 优先承接当前上下文，像聊天一样自然。\n"
            f"5. 优先服从 reply_instruction。\n"
            f"6. 如果外部知识库上下文不是“无”，并且和用户问题相关，必须优先使用知识库内容。\n"
            f"7. 如果用户询问事实、资料、设定、歌曲、口号、应援词、生日、专辑、人物关系，必须以知识库内容为准。\n"
            f"8. 如果知识库给出了明确答案，不要改写成知识库没有的说法。\n"
            f"9. 如果知识库没有答案，可以说明资料里没有明确写，不要编造。\n"
            f"10. 回复要符合角色口吻，简洁、自然。\n"
        )

    def _message_role_name(self, message: BaseMessage) -> str:
        if isinstance(message, HumanMessage):
            return "用户"
        if isinstance(message, AIMessage):
            return "助手"
        if isinstance(message, SystemMessage):
            return "系统"
        return getattr(message, "type", "unknown")

    def _message_text(self, message: BaseMessage) -> str:
        content = message.content

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
