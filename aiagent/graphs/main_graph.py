from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.graphs.llm_graph import LLMRunner
from aiagent.graphs.planner_graph import PlannerRunner
from aiagent.graphs.rag_graph import RAGRunner
from aiagent.graphs.state_graph import StateRunner
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import EmotionLabel, ResponsePacket


class MainGraphState(TypedDict, total=False):
    input_event: InputEvent
    persona_runtime: PersonaRuntime
    history: list[str]
    state_result: Any
    planner_result: Any
    rag_result: Any
    llm_result: Any
    response_packet: ResponsePacket
    metadata: dict[str, str]


class MainRunner:
    def __init__(
        self,
        state_runner: StateRunner,
        planner_runner: PlannerRunner,
        rag_runner: RAGRunner,
        llm_runner: LLMRunner,
    ) -> None:
        self.state_runner = state_runner
        self.planner_runner = planner_runner
        self.rag_runner = rag_runner
        self.llm_runner = llm_runner
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(MainGraphState)
        graph.add_node("prepare_context", self._prepare_context_node)
        graph.add_node("run_state_graph", self._run_state_graph_node)
        graph.add_node("run_planner_graph", self._run_planner_graph_node)
        graph.add_node("run_rag_graph", self._run_rag_graph_node)
        graph.add_node("run_llm_graph", self._run_llm_graph_node)
        graph.add_node("build_response_packet", self._build_response_packet_node)

        graph.add_edge(START, "prepare_context")
        graph.add_edge("prepare_context", "run_state_graph")
        graph.add_edge("run_state_graph", "run_planner_graph")
        graph.add_edge("run_planner_graph", "run_rag_graph")
        graph.add_edge("run_rag_graph", "run_llm_graph")
        graph.add_edge("run_llm_graph", "build_response_packet")
        graph.add_edge("build_response_packet", END)
        return graph.compile()

    def run(self, event: InputEvent, persona_runtime: PersonaRuntime, history: list[str] | None = None) -> ResponsePacket:
        return self.run_debug(event, persona_runtime, history)["response_packet"]

    def run_debug(
        self,
        event: InputEvent,
        persona_runtime: PersonaRuntime,
        history: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.graph.invoke(
            {
                "input_event": event,
                "persona_runtime": persona_runtime,
                "history": history or [],
            }
        )

    def _prepare_context_node(self, state: MainGraphState) -> dict[str, object]:
        history = list(state.get("history", []))
        return {
            "history": history,
            "metadata": {
                "main_graph": "started",
                "history_count": str(len(history)),
            },
        }

    def _run_state_graph_node(self, state: MainGraphState) -> dict[str, object]:
        event = state["input_event"]# type: ignore
        state_result = self.state_runner.run(
            user_text=event.text,
            user_name=event.user_name,
            persona_runtime=state["persona_runtime"],# type: ignore
            history=state.get("history", []),
        )
        metadata = dict(state.get("metadata", {}))
        metadata["state_graph"] = "done"
        return {"state_result": state_result, "metadata": metadata}

    def _run_planner_graph_node(self, state: MainGraphState) -> dict[str, object]:
        event = state["input_event"]# type: ignore
        planner_result = self.planner_runner.run(
            user_text=event.text,
            user_name=event.user_name,
            state_result=state["state_result"],# type: ignore
            persona_runtime=state["persona_runtime"],# type: ignore
        )
        metadata = dict(state.get("metadata", {}))
        metadata["planner_graph"] = "done"
        metadata["planner_retrieval_query"] = getattr(planner_result, "retrieval_query", "")
        return {"planner_result": planner_result, "metadata": metadata}

    def _run_rag_graph_node(self, state: MainGraphState) -> dict[str, object]:
        event = state["input_event"]# type: ignore
        state_result = state["state_result"]# type: ignore
        planner_result = state["planner_result"]# type: ignore

        rag_result = self.rag_runner.run(
            user_text=event.text,
            state_intent=getattr(state_result, "intent", ""),
            state_topic=getattr(state_result, "topic", ""),
            planner_query=getattr(planner_result, "retrieval_query", ""),
            planner_should_retrieve=bool(getattr(planner_result, "should_retrieve", False)),
        )

        metadata = dict(state.get("metadata", {}))
        metadata.update(rag_result.metadata)
        metadata["rag_query"] = rag_result.query
        metadata["rag_should_inject"] = str(rag_result.should_inject)
        metadata["rag_context_count"] = str(len(rag_result.context))
        return {"rag_result": rag_result, "metadata": metadata}

    def _run_llm_graph_node(self, state: MainGraphState) -> dict[str, object]:
        event = state["input_event"]# type: ignore
        rag_result = state["rag_result"]# type: ignore
        llm_result = self.llm_runner.run(
            thread_id=event.user_id,
            user_text=event.text,
            user_name=event.user_name,
            state_result=state["state_result"], # type: ignore
            planner_result=state["planner_result"],# type: ignore
            persona_runtime=state["persona_runtime"],# type: ignore
            retrieved_context=rag_result.context,
        )
        metadata = dict(state.get("metadata", {}))
        metadata["llm_graph"] = "done"
        return {"llm_result": llm_result, "metadata": metadata}

    def _build_response_packet_node(self, state: MainGraphState) -> dict[str, object]:
        llm_result = state["llm_result"]# type: ignore
        metadata = dict(state.get("metadata", {}))
        metadata.update(llm_result.metadata)

        packet = ResponsePacket(
            reply_text=llm_result.reply_text,
            base_reply_text=llm_result.reply_text,
            emotion=self._to_emotion_label(llm_result.target_emotion),
            should_speak=llm_result.should_speak,
            should_store_memory=llm_result.should_store_memory,
            motion=llm_result.target_motion,
            expression=llm_result.target_expression,
            metadata=metadata,
        )
        return {"response_packet": packet}

    def clear_thread(self, thread_id: str) -> None:
        self.llm_runner.clear_thread(thread_id)

    def clear_all_threads(self) -> None:
        self.llm_runner.clear_all_threads()

    def _to_emotion_label(self, emotion: str) -> EmotionLabel:
        try:
            return EmotionLabel((emotion or "").strip().lower())
        except ValueError:
            return EmotionLabel.NEUTRAL
