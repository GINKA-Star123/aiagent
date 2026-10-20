import os

import pytest
from langchain_core.messages import HumanMessage

from aiagent.graphs.llm_graph import LLMRunner
from aiagent.state.redis_state_store import RedisStateStore
from aiagent.state.shared_state import ThreadOwnerRecord

pytestmark = pytest.mark.integration


def redis_url() -> str:
    value = os.getenv("TEST_REDIS_URL", "")
    if not value:
        pytest.skip("TEST_REDIS_URL is not configured")
    return value


def test_user_thread_registration_is_visible_across_store_instances():
    first = RedisStateStore(redis_url(), prefix="aiagent:test:v12:contract")
    second = RedisStateStore(redis_url(), prefix="aiagent:test:v12:contract")
    first.redis.flushdb()

    first.register_thread(
        ThreadOwnerRecord(
            thread_id="thread-a",
            user_id="user-a",
            session_id="session-a",
        )
    )
    assert second.list_user_threads("user-a") == ["thread-a"]

    second.delete_thread_registration("thread-a", "user-a")
    assert first.list_user_threads("user-a") == []


def test_session_lock_rejects_concurrent_owner():
    first = RedisStateStore(redis_url(), prefix="aiagent:test:v12:lock")
    second = RedisStateStore(redis_url(), prefix="aiagent:test:v12:lock")
    first.redis.flushdb()

    with first.session_lock("session-a"):
        with pytest.raises(Exception) as caught:
            with second.session_lock("session-a"):
                pass
        assert "session" in str(caught.value)


class _StubSettings:
    enable_mock_llm = True
    llm_provider = "mock"


class _StubService:
    settings = _StubSettings()


def _redis_saver(url: str, prefix: str):
    """与 apps/core/bootstrap.build_llm_checkpointer 相同的构造方式。"""
    from langgraph.checkpoint.redis import RedisSaver

    saver = RedisSaver(
        redis_url=url,
        checkpoint_prefix=f"{prefix}:checkpoint",
        checkpoint_write_prefix=f"{prefix}:checkpoint-write",
    )
    saver.setup()
    return saver


def test_two_workers_share_history_through_redis():
    """两个 Worker 各持一个 RedisSaver、共用同一 Redis 时，短期上下文必须连续。"""
    url = redis_url()
    prefix = "aiagent:test:v12:runner"
    store = RedisStateStore(url, prefix=prefix)
    store.redis.flushdb()

    worker_a = LLMRunner(
        llm_service=_StubService(),
        shared_state_store=store,
        checkpointer=_redis_saver(url, prefix),
    )
    worker_b = LLMRunner(
        llm_service=_StubService(),
        shared_state_store=store,
        checkpointer=_redis_saver(url, prefix),
    )

    thread_id = "shared-history"
    store.register_thread(
        ThreadOwnerRecord(thread_id=thread_id, user_id="user-a", session_id=thread_id)
    )
    worker_a.graph.update_state(
        {"configurable": {"thread_id": thread_id}},
        {"messages": [HumanMessage(content="continuity-marker")]},
        as_node="normalize_reply",
    )

    own_history = worker_a.recent_dialogue_lines(thread_id=thread_id)
    other_history = worker_b.recent_dialogue_lines(thread_id=thread_id)
    assert any("continuity-marker" in line for line in own_history)
    assert other_history == own_history

    cleared = worker_b.clear_user_threads("user-a")
    assert cleared == [thread_id]
    assert worker_a.recent_dialogue_lines(thread_id=thread_id) == []
    assert store.get_thread_owner(thread_id) is None
