from __future__ import annotations

from typing import Any

from aiagent.graphs.graph_model import NO_LONG_TERM_MEMORY_TEXT, RAGGraphResult
from aiagent.graphs.metadata_utils import metadata_strings

RAG_DEGRADED_REASON = "rag_graph_failed"
MEMORY_DEGRADED_STATUS = "degraded"

def build_degraded_rag_result(
        *,
        query: str = "",
        reason: str = RAG_DEGRADED_REASON,
        metadata: dict[str, Any] | None = None,
) -> RAGGraphResult:
    """
    构造"检索不可用/失败"时的空结果
    """

    raw_metadata = dict(metadata or {})
    safe_metadata = {str(key): value for key,value in (raw_metadata.items())}

    return RAGGraphResult(
        query=query,
        should_inject=False,
        context=[],
        debug_chunks=[],
        citations=[],
        confidence={},
        reason=reason,
        metadata=metadata_strings(safe_metadata)
    )

def build_degraded_memory_retrieve_state(
        *,
        user_id: str,
        agent_id: str,
        metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    记忆检索不可用时的降级状态(MemoryGraphState 的子集)
    """

    return {
        "user_id": user_id,
        "agent_id": agent_id,
        "memory_hits": [],
        "memory_pinned_records": [],
        "memory_prompt_context": NO_LONG_TERM_MEMORY_TEXT,
        "memory_prompt_context_data": {},
        "metadata": dict(metadata or {}),
    }

def build_degraded_memory_store_state(
        *,
        user_id: str,
        agent_id: str,
        error: Exception | str,
        metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    记忆写入不可用时的降级状态
    """

    return {
        "user_id": user_id,
        "agent_id": agent_id,
        "store_result":{
            "ok": False,
            "status": MEMORY_DEGRADED_STATUS,
            "error": str(error),
        },
        "metadata": dict(metadata or {}),
    }