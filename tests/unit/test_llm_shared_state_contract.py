from __future__ import annotations

from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from aiagent.graphs.llm_graph import LLMRunner
from aiagent.state.shared_state import SharedStateOwnershipError, ThreadOwnerRecord


class StubSettings:
    enable_mock_llm = True
    llm_provider = "mock"


class StubService:
    settings = StubSettings()


class FakeSharedStore:
    """共享状态替身：只实现 LLMRunner 真正调用的接口，让契约测试不依赖 Redis。

    行为必须与 aiagent/state/redis_state_store.py 保持一致（归属校验、按用户索引、全局枚举）。
    """

    def __init__(self) -> None:
        self.owners: dict[str, ThreadOwnerRecord] = {}
        self.user_threads: dict[str, set[str]] = {}

    def register_thread(self, record: ThreadOwnerRecord) -> None:
        existing = self.owners.get(record.thread_id)
        if existing is not None and (
            existing.user_id != record.user_id or existing.session_id != record.session_id
        ):
            raise SharedStateOwnershipError("thread belongs to another owner")
        self.owners[record.thread_id] = record
        self.user_threads.setdefault(record.user_id, set()).add(record.thread_id)

    def get_thread_owner(self, thread_id: str) -> ThreadOwnerRecord | None:
        return self.owners.get(thread_id)

    def list_user_threads(self, user_id: str) -> list[str]:
        return sorted(self.user_threads.get(user_id, set()))

    def list_all_threads(self) -> list[str]:
        return sorted(self.owners)

    def delete_thread_registration(self, thread_id: str, user_id: str) -> None:
        owner = self.owners.get(thread_id)
        if owner is not None and owner.user_id != user_id:
            raise SharedStateOwnershipError("cannot delete another user's thread")
        self.owners.pop(thread_id, None)
        self.user_threads.get(user_id, set()).discard(thread_id)


def build_runner_pair() -> tuple[LLMRunner, LLMRunner, FakeSharedStore]:
    """构造两个共享同一份 checkpointer 与共享状态存储的 Worker。"""
    checkpointer = InMemorySaver()
    store = FakeSharedStore()
    first = LLMRunner(llm_service=StubService(), shared_state_store=store, checkpointer=checkpointer)
    second = LLMRunner(llm_service=StubService(), shared_state_store=store, checkpointer=checkpointer)
    return first, second, store


def seed_thread(runner: LLMRunner, thread_id: str, user_id: str, text: str) -> None:
    """登记归属并写入一条检查点，等价于一次真实对话产生的共享状态。"""
    runner.shared_state_store.register_thread(
        ThreadOwnerRecord(thread_id=thread_id, user_id=user_id, session_id=thread_id)
    )
    runner._thread_users[thread_id] = user_id
    runner.graph.update_state(
        {"configurable": {"thread_id": thread_id}},
        {"messages": [HumanMessage(content=text)]},
        as_node="normalize_reply",
    )


def test_checkpoint_is_visible_to_another_runner():
    first, second, _store = build_runner_pair()
    thread_id = f"shared-contract:{uuid4().hex}"
    seed_thread(first, thread_id, "owner-a", "continuity-marker")

    own_history = first.recent_dialogue_lines(thread_id=thread_id)
    shared_history = second.recent_dialogue_lines(thread_id=thread_id)

    assert any("continuity-marker" in line for line in own_history)
    assert shared_history == own_history


def test_user_cleanup_reaches_other_runner_without_touching_other_user():
    first, second, store = build_runner_pair()
    first_thread = f"owner-a:{uuid4().hex}"
    other_thread = f"owner-b:{uuid4().hex}"
    seed_thread(first, first_thread, "owner-a", "delete-marker")
    seed_thread(first, other_thread, "owner-b", "retain-marker")

    cleared = second.clear_user_threads("owner-a")

    assert cleared == [first_thread]
    assert first.recent_dialogue_lines(thread_id=first_thread) == []
    retained = first.recent_dialogue_lines(thread_id=other_thread)
    assert any("retain-marker" in line for line in retained)
    assert store.get_thread_owner(other_thread) is not None


def test_clear_all_threads_reaches_thread_never_seen_locally():
    first, second, store = build_runner_pair()
    thread_id = f"owner-c:{uuid4().hex}"
    seed_thread(first, thread_id, "owner-c", "global-reset-marker")

    second.clear_all_threads()

    assert first.recent_dialogue_lines(thread_id=thread_id) == []
    assert store.list_all_threads() == []


def test_shared_mode_rejects_empty_user_id():
    first, _second, _store = build_runner_pair()

    with pytest.raises(SharedStateOwnershipError):
        first.run(
            thread_id="thread-without-owner",
            user_text="hi",
            user_name="tester",
            state_result=None,
            planner_result=None,
            persona_runtime=None,
        )
