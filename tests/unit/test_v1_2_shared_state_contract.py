import os
import pytest

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