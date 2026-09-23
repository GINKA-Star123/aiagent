"""RAG / Memory 降级路径单测（roadmap 5.2）。"""

from __future__ import annotations

from typing import Any

from aiagent.graphs.degradation import (
    RAG_DEGRADED_REASON,
    build_degraded_rag_result,
)
from aiagent.graphs.graph_model import RAGGraphInput
from aiagent.graphs.memory_graph import MemoryRunner
from aiagent.graphs.rag_graph import RAGRunner
from aiagent.schemas.memory import (
    MemoryCategory,
    MemoryImportance,
    MemoryStorePlan,
    MemoryWriteDecision,
)


class _FailingGraph:
    def invoke(self, *_args: Any, **_kwargs: Any):
        raise RuntimeError("graph invoke failed (unit test)")


class _FailingMemory:
    def search(self, **_kwargs: Any):
        raise RuntimeError("mem0 unavailable (unit test)")

    def list_pinned_records(self, **_kwargs: Any):
        raise RuntimeError("mem0 unavailable (unit test)")

    def add_turn(self, **_kwargs: Any):
        raise RuntimeError("mem0 unavailable (unit test)")


class _FailingPipeline:
    def search(self, **_kwargs: Any):
        raise RuntimeError("qdrant unavailable (unit test)")

    def debug_retrieve(self, **_kwargs: Any):
        raise RuntimeError("qdrant unavailable (unit test)")


class _FailingIntake:
    def build_store_plan(self, **_kwargs: Any):
        raise RuntimeError("intake failed (unit test)")


class _EnabledPreferences:
    def is_enabled(self, **_kwargs: Any) -> bool:
        return True


# ------------------------- RAG -------------------------


def test_build_degraded_rag_result_is_empty_and_stringified():
    result = build_degraded_rag_result(
        query="乐正绫是谁",
        metadata={"rag_error": "boom", "rag_graph_status": "failed"},
    )

    assert result.should_inject is False
    assert result.context == []
    assert result.reason == RAG_DEGRADED_REASON
    assert result.metadata["rag_error"] == "boom"
    assert all(isinstance(value, str) for value in result.metadata.values())


def test_rag_run_degrades_when_graph_invoke_fails(monkeypatch):
    runner = RAGRunner(rag_pipeline=object())
    monkeypatch.setattr(runner, "graph", _FailingGraph())

    result = runner.run(user_text="你好", planner_should_retrieve=True)

    assert result.should_inject is False
    assert result.context == []
    assert result.reason == RAG_DEGRADED_REASON
    assert result.metadata["rag_graph_status"] == "failed"
    assert result.metadata["rag_error"]


def test_rag_retrieve_node_records_rag_error():
    runner = RAGRunner(rag_pipeline=_FailingPipeline())
    state = {
        "input": RAGGraphInput(user_text="你好", planner_should_retrieve=True),
        "query": "你好",
        "metadata": {},
    }

    result = runner._retrieve_node(state)

    assert result["raw_context"] == []
    assert result["metadata"]["rag_retrieve_status"] == "failed"
    assert "qdrant unavailable" in result["metadata"]["rag_error"]


# ------------------------- Memory -------------------------


def test_memory_retrieve_node_records_memory_error():
    runner = MemoryRunner(memory=_FailingMemory(), policy_service=None)
    state = {"user_id": "u1", "user_text": "hi", "retrieval_query": "hi"}

    result = runner._retrieve_node(state)

    assert result["memory_hits"] == []
    assert result["memory_prompt_context"] == "无长期记忆。"
    assert result["metadata"]["memory_retrieve_status"] == "failed"
    assert "mem0 unavailable" in result["metadata"]["memory_error"]


def test_memory_retrieve_before_reply_degrades_when_node_raises(monkeypatch):
    runner = MemoryRunner(memory=_FailingMemory(), policy_service=None)
    runner.preference_store = _EnabledPreferences()

    def _boom(_state):
        raise RuntimeError("retrieve exploded (unit test)")

    monkeypatch.setattr(runner, "_retrieve_node", _boom)

    result = runner.retrieve_before_reply(user_id="u1", user_text="hi")

    assert result["memory_hits"] == []
    assert result["memory_prompt_context"] == "无长期记忆。"
    assert "retrieve exploded" in result["metadata"]["memory_error"]


def test_memory_guard_write_degrades_on_plan_error():
    runner = MemoryRunner(memory=_FailingMemory(), policy_service=None)
    runner.intake_service = _FailingIntake()
    state = {"metadata": {}, "user_text": "hi", "assistant_text": "yo", "memory_hits": []}

    result = runner._guard_write_node(state)

    assert result["memory_store_plan"] is None
    assert result["metadata"]["memory_guard_write_status"] == "failed"
    assert "intake failed" in result["metadata"]["memory_error"]
    assert runner._route_after_guard(result) == "end"


def test_memory_run_after_reply_degrades_when_graph_invoke_fails(monkeypatch):
    runner = MemoryRunner(memory=_FailingMemory(), policy_service=None)
    runner.preference_store = _EnabledPreferences()
    monkeypatch.setattr(runner, "graph", _FailingGraph())

    result = runner.run_after_reply(
        user_id="u1",
        user_name="U",
        session_id="chat:u1",
        turn_id="chat:u1:abcd1234",
        user_text="hi",
        assistant_text="yo",
        retrieval_query="hi",
        planner_should_store_memory=True,
    )

    assert result["store_result"]["ok"] is False
    assert result["store_result"]["status"] == "degraded"
    assert result["metadata"]["memory_store_status"] == "failed"
    assert "graph invoke failed" in result["metadata"]["memory_error"]


def test_memory_store_node_records_memory_error():
    runner = MemoryRunner(memory=_FailingMemory(), policy_service=None)

    decision = MemoryWriteDecision(
        should_store=True,
        category=MemoryCategory.PREFERENCE,
        importance=MemoryImportance.MEDIUM,
        reason="unit test",
        memory_hint="prefers tea",
        confidence=0.9,
    )
    plan = MemoryStorePlan(
        should_store=True,
        status="approved",
        reason="unit test",
        category=MemoryCategory.PREFERENCE,
        importance=MemoryImportance.MEDIUM,
        memory_text="用户喜欢茶",
    )

    result = runner._store_node(
        {
            "user_id": "u1",
            "user_name": "U",
            "user_text": "hi",
            "assistant_text": "yo",
            "session_id": "chat:u1",
            "turn_id": "chat:u1:abcd1234",
            "write_decision": decision,
            "memory_store_plan": plan,
            "metadata": {},
        }
    )

    assert result["store_result"]["ok"] is False
    assert result["store_result"]["status"] == "failed"
    assert "mem0 unavailable" in result["metadata"]["memory_error"]

    # 顺带守住 _store_node 回填的元数据（这些键在失败路径也必须存在）
    assert result["metadata"]["memory_store_status"] == "failed"
    assert result["metadata"]["category"] == "preference"
    assert result["metadata"]["memory_layer"] == "preference"
    assert result["metadata"]["memory_guard_status"] == "approved"

def test_build_degraded_rag_result_handles_none_metadata():
    result = build_degraded_rag_result(metadata=None)

    assert result.metadata == {}
    assert result.should_inject is False


def test_build_degraded_rag_result_stringifies_ctypes():
    result = build_degraded_rag_result(metadata={"rag_error": "boom", "rag_retry": 3})

    assert result.metadata["rag_error"] == "boom"
    assert result.metadata["rag_retry"] == "3"