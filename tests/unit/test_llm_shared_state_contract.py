from uuid import uuid4

from langchain_core.messages import HumanMessage

from aiagent.graphs.llm_graph import LLMRunner


class StubSettings:
    enable_mock_llm = True
    llm_provider = "mock"


class StubService:
    settings = StubSettings()


def seed_thread(runner, thread_id, user_id, text):
    runner._thread_users[thread_id] = user_id
    runner.graph.update_state(
        {"configurable": {"thread_id": thread_id}},
        {"messages": [HumanMessage(content=text)]},
        as_node="normalize_reply",
    )


def test_checkpoint_is_visible_to_another_runner():
    first = LLMRunner(llm_service=StubService())
    second = LLMRunner(llm_service=StubService())
    thread_id = f"shared-contract:{uuid4().hex}"
    seed_thread(first, thread_id, "owner-a", "continuity-marker")

    own_history = first.recent_dialogue_lines(thread_id=thread_id)
    shared_history = second.recent_dialogue_lines(thread_id=thread_id)

    assert any("continuity-marker" in line for line in own_history)
    assert shared_history == own_history


def test_user_cleanup_reaches_other_runner_without_touching_other_user():
    first = LLMRunner(llm_service=StubService())
    second = LLMRunner(llm_service=StubService())
    first_thread = f"owner-a:{uuid4().hex}"
    other_thread = f"owner-b:{uuid4().hex}"
    seed_thread(first, first_thread, "owner-a", "delete-marker")
    seed_thread(first, other_thread, "owner-b", "retain-marker")

    second.clear_user_threads("owner-a")

    assert first.recent_dialogue_lines(thread_id=first_thread) == []
    retained = first.recent_dialogue_lines(thread_id=other_thread)
    assert any("retain-marker" in line for line in retained)