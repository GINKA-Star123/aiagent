from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.graphs.graph_model import RAGGraphInput, RAGGraphResult

from aiagent.graphs.metadata_utils import (
    mark_stage_done,
    mark_stage_failed,
    mark_stage_started,
    mark_stage_skipped,
    metadata_strings,
    now_perf,
)
from aiagent.knowledge.query_normalizer import normalize_rag_query
from aiagent.knowledge.rag_citations import build_rag_citations, citations_to_metadata
from aiagent.knowledge.rag_confidence import evaluate_rag_confidence

class RAGGraphState(TypedDict, total=False):
    input: RAGGraphInput
    query: str
    raw_context: list[str]
    raw_debug: list[dict[str, Any]]
    filtered_context: list[str]
    filtered_debug: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    confidence: dict[str, Any]
    result: RAGGraphResult
    metadata: dict[str, str]


class RAGRunner:
    def __init__(
        self,
        rag_pipeline: Any,
        top_k: int = 4,
        min_cosine_score: float = 0.38,
        require_relevance: bool = True,
    ) -> None:
        self.rag_pipeline = rag_pipeline
        self.top_k = top_k
        self.min_cosine_score = min_cosine_score
        self.require_relevance = require_relevance
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(RAGGraphState)
        graph.add_node("build_query", self._build_query_node)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("filter_relevance", self._filter_relevance_node)
        graph.add_node("pack_context", self._pack_context_node)

        graph.add_edge(START, "build_query")
        graph.add_edge("build_query", "retrieve")
        graph.add_edge("retrieve", "filter_relevance")
        graph.add_edge("filter_relevance", "pack_context")
        graph.add_edge("pack_context", END)
        return graph.compile()

    def run(
        self,
        user_text: str,
        state_intent: str = "",
        state_topic: str = "",
        planner_query: str = "",
        planner_should_retrieve: bool = False,
    ) -> RAGGraphResult:
        started_at = now_perf()
        result = self.graph.invoke(
            {
                "input": RAGGraphInput(
                    user_text=user_text,
                    state_intent=state_intent,
                    state_topic=state_topic,
                    planner_query=planner_query,
                    planner_should_retrieve=planner_should_retrieve,
                )
            }
        )
        metadata = mark_stage_done(
            dict(result.get("metadata", {})),
            "rag_graph",
            started_at,
        )
        rag_result = result["result"]
        rag_result.metadata = metadata_strings(metadata)
        return rag_result

    def _build_query_node(self, state: RAGGraphState) -> dict[str, object]:
        started_at = now_perf()
        graph_input = state["input"] # type: ignore
        query = self._build_search_query(
            user_text=graph_input.user_text,
            planner_query=graph_input.planner_query,
            state_topic=graph_input.state_topic,
        )

        metadata = mark_stage_done(
            mark_stage_started(
                {
                    "rag_query_source": "planner+fallback"
                    if graph_input.planner_query.strip()
                    else "fallback",
                    "planner_should_retrieve": graph_input.planner_should_retrieve,
                },
                "rag_graph",
            ),
            "rag_build_query",
            started_at,
            rag_query=query,
        )

        return {
            "query": query,
            "metadata": metadata,
        }

    def _retrieve_node(self, state: RAGGraphState) -> dict[str, object]:
        graph_input = state["input"] # type: ignore
        if not graph_input.planner_should_retrieve:
            metadata = mark_stage_skipped(
                state.get("metadata", {}),
                "rag_retrieve",
                "planner_should_retrieve_false",
            )
            return {
                "raw_context": [],
                "raw_debug": [],
                "metadata": metadata,
            }

        started_at = now_perf()
        query = state["query"] # type: ignore
        metadata = dict(state.get("metadata", {}))

        try:
            raw_context = self.rag_pipeline.search(query=query, top_k=self.top_k)
            raw_debug = self.rag_pipeline.debug_retrieve(query=query, top_k=self.top_k)
        except Exception as exc:
            metadata = mark_stage_failed(
                metadata,
                "rag_retrieve",
                started_at,
                exc,
            )
            return {
                "raw_context": [],
                "raw_debug": [],
                "metadata": metadata,
            }

        metadata = mark_stage_done(
            metadata,
            "rag_retrieve",
            started_at,
            rag_raw_count = len(raw_context),
        )

        return {
            "raw_context": raw_context,
            "raw_debug": raw_debug,
            "metadata": metadata,
        }
         

    def _filter_relevance_node(self, state: RAGGraphState) -> dict[str, object]:
        raw_context = list(state.get("raw_context", []))
        raw_debug = list(state.get("raw_debug", []))
        metadata = dict(state.get("metadata", {}))

        if not raw_context or not raw_debug:
            confidence = evaluate_rag_confidence([], min_cosine_score=self.min_cosine_score)
            metadata.update(confidence.to_metadata(prefix="rag"))
            metadata["rag_filter"] = "empty"
            return {
                "filtered_context": [],
                "filtered_debug": raw_debug,
                "citations": [],
                "confidence": confidence.model_dump(mode="json"),
                "metadata": metadata,
            }

        confidence = evaluate_rag_confidence(
            raw_debug,
            min_cosine_score=self.min_cosine_score,
            allow_bm25_only=True,
        )
        metadata.update(confidence.to_metadata(prefix="rag"))

        if not self.require_relevance:
            citations = build_rag_citations(raw_debug, max_citations=self.top_k)
            metadata["rag_filter"] = "disabled"
            metadata.update(citations_to_metadata(citations, prefix="rag"))
            return {
                "filtered_context": raw_context,
                "filtered_debug": raw_debug,
                "citations": [citation.model_dump(mode="json") for citation in citations],
                "confidence": confidence.model_dump(mode="json"),
                "metadata": metadata,
            }

        if confidence.should_inject:
            citations = build_rag_citations(raw_debug, max_citations=self.top_k)
            metadata["rag_filter"] = "passed"
            metadata.update(citations_to_metadata(citations, prefix="rag"))
            return {
                "filtered_context": raw_context,
                "filtered_debug": raw_debug,
                "citations": [citation.model_dump(mode="json") for citation in citations],
                "confidence": confidence.model_dump(mode="json"),
                "metadata": metadata,
            }

        metadata["rag_filter"] = "low_relevance"
        metadata.update(citations_to_metadata([], prefix="rag"))
        return {
            "filtered_context": [],
            "filtered_debug": raw_debug,
            "citations": [],
            "confidence": confidence.model_dump(mode="json"),
            "metadata": metadata,
        }

    def _pack_context_node(self, state: RAGGraphState) -> dict[str, object]:
        context = list(state.get("filtered_context", []))
        debug = list(state.get("filtered_debug", []))
        citations = list(state.get("citations", []))
        confidence = dict(state.get("confidence", {}))
        metadata = dict(state.get("metadata", {}))
        query = str(state.get("query", ""))

        result = RAGGraphResult(
            query=query,
            should_inject=bool(context),
            context=context,
            debug_chunks=debug,
            citations=citations,
            confidence=confidence,
            reason=metadata.get("rag_filter", ""),
            metadata=metadata_strings(metadata),
        )
        return {"result": result}

    
    def _build_search_query(self, user_text: str, planner_query: str = "", state_topic: str = "") -> str:
        base_parts = [
            planner_query.strip(),
            user_text.strip(),
            state_topic.strip(),
        ]
        query = " ".join(part for part in base_parts if part)
        return normalize_rag_query(query)
