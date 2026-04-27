from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.graphs.graph_model import RAGGraphInput, RAGGraphResult


class RAGGraphState(TypedDict, total=False):
    input: RAGGraphInput
    query: str
    raw_context: list[str]
    raw_debug: list[dict[str, Any]]
    filtered_context: list[str]
    filtered_debug: list[dict[str, Any]]
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
        return result["result"]

    def _build_query_node(self, state: RAGGraphState) -> dict[str, object]:
        graph_input = state["input"] # type: ignore
        query = self._build_search_query(
            user_text=graph_input.user_text,
            planner_query=graph_input.planner_query,
            state_topic=graph_input.state_topic,
        )

        return {
            "query": query,
            "metadata": {
                "rag_graph": "started",
                "rag_query_source": "planner+fallback"
                if graph_input.planner_query.strip()
                else "fallback",
                "planner_should_retrieve": str(graph_input.planner_should_retrieve),
            },
        }

    def _retrieve_node(self, state: RAGGraphState) -> dict[str, object]:
        query = state["query"] # type: ignore
        metadata = dict(state.get("metadata", {}))

        try:
            raw_context = self.rag_pipeline.search(query=query, top_k=self.top_k)
            raw_debug = self.rag_pipeline.debug_retrieve(query=query, top_k=self.top_k)
            metadata["rag_retrieve"] = "done"
            metadata["rag_raw_count"] = str(len(raw_context))
            return {
                "raw_context": raw_context,
                "raw_debug": raw_debug,
                "metadata": metadata,
            }
        except Exception as exc:
            metadata["rag_retrieve"] = "failed"
            metadata["rag_error"] = str(exc)
            return {
                "raw_context": [],
                "raw_debug": [],
                "metadata": metadata,
            }

    def _filter_relevance_node(self, state: RAGGraphState) -> dict[str, object]:
        raw_context = list(state.get("raw_context", []))
        raw_debug = list(state.get("raw_debug", []))
        metadata = dict(state.get("metadata", {}))

        if not raw_context or not raw_debug:
            metadata["rag_filter"] = "empty"
            return {
                "filtered_context": [],
                "filtered_debug": raw_debug,
                "metadata": metadata,
            }

        if not self.require_relevance:
            metadata["rag_filter"] = "disabled"
            return {
                "filtered_context": raw_context,
                "filtered_debug": raw_debug,
                "metadata": metadata,
            }

        relevance = self._judge_relevance(raw_debug)
        metadata["rag_relevance_reason"] = relevance["reason"]
        metadata["rag_best_cosine"] = str(relevance["best_cosine"])
        metadata["rag_best_sources"] = ",".join(relevance["best_sources"])

        if relevance["passed"]:
            metadata["rag_filter"] = "passed"
            return {
                "filtered_context": raw_context,
                "filtered_debug": raw_debug,
                "metadata": metadata,
            }

        metadata["rag_filter"] = "low_relevance"
        return {
            "filtered_context": [],
            "filtered_debug": raw_debug,
            "metadata": metadata,
        }

    def _pack_context_node(self, state: RAGGraphState) -> dict[str, object]:
        context = list(state.get("filtered_context", []))
        debug = list(state.get("filtered_debug", []))
        metadata = dict(state.get("metadata", {}))
        query = str(state.get("query", ""))

        result = RAGGraphResult(
            query=query,
            should_inject=bool(context),
            context=context,
            debug_chunks=debug,
            reason=metadata.get("rag_filter", ""),
            metadata=metadata,
        )
        return {"result": result}

    def _judge_relevance(self, debug_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        best_cosine = 0.0
        best_sources: set[str] = set()

        for chunk in debug_chunks:
            sources = set(chunk.get("retrieval_sources", []))
            cosine_score = chunk.get("cosine_score")
            bm25_rank = chunk.get("bm25_rank")
            vector_rank = chunk.get("vector_rank")

            if sources:
                best_sources.update(str(source) for source in sources)

            if isinstance(cosine_score, (int, float)):
                best_cosine = max(best_cosine, float(cosine_score))

            if {"bm25", "vector"}.issubset(sources):
                return {
                    "passed": True,
                    "reason": "hybrid_match",
                    "best_cosine": best_cosine,
                    "best_sources": sorted(best_sources),
                }

            if isinstance(cosine_score, (int, float)) and cosine_score >= self.min_cosine_score:
                return {
                    "passed": True,
                    "reason": "vector_score",
                    "best_cosine": best_cosine,
                    "best_sources": sorted(best_sources),
                }

            if isinstance(bm25_rank, int) and bm25_rank <= 2 and vector_rank is not None:
                return {
                    "passed": True,
                    "reason": "bm25_top_with_vector_candidate",
                    "best_cosine": best_cosine,
                    "best_sources": sorted(best_sources),
                }

        return {
            "passed": False,
            "reason": "no_reliable_candidate",
            "best_cosine": best_cosine,
            "best_sources": sorted(best_sources),
        }

    def _build_search_query(self, user_text: str, planner_query: str = "", state_topic: str = "") -> str:
        base_parts = [
            planner_query.strip(),
            user_text.strip(),
            state_topic.strip(),
        ]
        query = " ".join(part for part in base_parts if part)
        query = self._normalize_aliases(query)
        query = self._expand_domain_terms(query)
        return query.strip()

    def _normalize_aliases(self, query: str) -> str:
        aliases = {
            "天依": "洛天依",
            "阿绫": "乐正绫",
            "阿綾": "乐正绫",
            "龙牙": "乐正龙牙",
            "龍牙": "乐正龙牙",
            "摩柯": "徵羽摩柯",
            "墨姐": "墨清弦",
            "清弦": "墨清弦",
            "言和和": "言和",
        }

        normalized = query
        for alias, canonical in aliases.items():
            if alias in normalized and canonical not in normalized:
                normalized = normalized.replace(alias, f"{alias} {canonical}")

        return normalized

    def _expand_domain_terms(self, query: str) -> str:
        expansions: list[str] = []

        if any(term in query for term in ["应援词", "应援口号", "口号", "slogan"]):
            expansions.extend(["口号", "应援词", "应援口号", "华风夏韵", "洛水天依"])

        if any(term in query for term in ["歌曲", "有什么歌", "有哪些歌", "代表曲", "曲子"]):
            expansions.extend(["相关歌曲", "代表曲", "官方专辑", "歌词"])

        if any(term in query for term in ["专辑", "EP", "唱片"]):
            expansions.extend(["官方专辑", "发行", "收录曲"])

        if any(term in query for term in ["生日", "诞生日", "生贺"]):
            expansions.extend(["生日", "诞生祭", "生贺曲"])

        if any(term in query for term in ["设定", "人设", "资料", "介绍"]):
            expansions.extend(["设定", "角色资料", "代表色", "声源", "生日"])

        if not expansions:
            return query

        merged = query
        for item in expansions:
            if item not in merged:
                merged += f" {item}"

        return merged
