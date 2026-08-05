import pytest

from apps.core.capabilities import CapabilityRegistry, CapabilityStatus
from apps.core.lazy_component import LazyComponent
from aiagent.knowledge.null_rag_pipeline import NullRAGPipeline
from aiagent.memory.null_memory import NullLongTermMemory


def test_capability_registry_snapshot_counts_statuses():
    registry = CapabilityRegistry()

    registry.mark_available("llm", "LLM is ready.")
    registry.mark_degraded("rag", "RAG is degraded.", error="missing index")
    registry.mark_disabled("live2d", "Live2D is disabled.")

    snapshot = registry.snapshot()

    assert snapshot["ok"] is True
    assert snapshot["status"] == "degraded"
    assert snapshot["summary"]["available"] == 1
    assert snapshot["summary"]["degraded"] == 1
    assert snapshot["summary"]["disabled"] == 1
    assert snapshot["items"]["llm"]["status"] == CapabilityStatus.AVAILABLE
    assert snapshot["items"]["rag"]["error"] == "missing index"


def test_null_rag_pipeline_is_safe():
    rag = NullRAGPipeline(reason="unit disabled")

    assert rag.search("hello") == []
    assert rag.debug_retrieve("hello") == []
    assert rag.format_for_prompt("hello") == "无外部知识。"

    stats = rag.stats()
    assert stats["ok"] is False
    assert stats["degraded"] is True
    assert stats["reason"] == "unit disabled"


def test_null_long_term_memory_is_safe():
    memory = NullLongTermMemory(reason="unit disabled")

    assert memory.search(query="hello", user_id="u1") == []
    assert memory.get_all(user_id="u1") == []
    assert memory.format_for_prompt([]) == "无长期记忆。"

    add_result = memory.add_turn(
        user_id="u1",
        user_name="tester",
        user_text="hello",
        assistant_text="hi",
        session_id="s1",
        turn_id="t1",
    )
    assert add_result["status"] == "skipped"
    assert add_result["degraded"] is True
    assert memory.list_pinned_records(user_id="u1") == []

def test_lazy_component_marks_available_after_get():
    registry = CapabilityRegistry()

    lazy_value = LazyComponent(
        name="unit_lazy",
        factory=lambda: {"ok": True},
        capabilities=registry,
        summary="Unit lazy component",
    )

    before = registry.get("unit_lazy")
    assert before is not None
    assert before.status == CapabilityStatus.DISABLED

    value = lazy_value.get()

    assert value == {"ok": True}
    after = registry.get("unit_lazy")
    assert after is not None
    assert after.status == CapabilityStatus.AVAILABLE


def test_lazy_component_marks_error_when_factory_fails():
    registry = CapabilityRegistry()

    def fail():
        raise RuntimeError("unit boom")

    lazy_value = LazyComponent(
        name="unit_lazy_fail",
        factory=fail,
        capabilities=registry,
        summary="Unit failing lazy component",
    )

    with pytest.raises(RuntimeError):
        lazy_value.get()

    record = registry.get("unit_lazy_fail")
    assert record is not None
    assert record.status == CapabilityStatus.ERROR
    assert "unit boom" in record.error