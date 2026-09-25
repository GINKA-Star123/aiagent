import pytest
from langchain_core.messages import HumanMessage
from aiagent.graphs.llm_graph import LLMRunner


class StubSettings:
    enable_mock_llm = True
    llm_provider = "mock"


class StubService:
    settings = StubSettings()


def test_delete_thread_removes_checkpoint_and_preserves_other_thread():
    runner = LLMRunner(llm_service=StubService())
    for thread_id in ("target", "other"):
        runner.graph.update_state(
            {"configurable": {"thread_id": thread_id}},
            {"messages": [HumanMessage(content=f"{thread_id}-marker")]},
            as_node="normalize_reply",
        )
    assert runner.recent_dialogue_lines("target")
    runner.clear_thread("target")
    runner.clear_thread("target")
    assert runner.recent_dialogue_lines("target") == []
    assert list(runner.checkpointer.list(
        {"configurable": {"thread_id": "target"}}
    )) == []
    assert any("other-marker" in s for s in runner.recent_dialogue_lines("other"))


def test_delete_thread_rejects_empty_id():
    with pytest.raises(ValueError):
        LLMRunner(llm_service=StubService()).clear_thread(" ")