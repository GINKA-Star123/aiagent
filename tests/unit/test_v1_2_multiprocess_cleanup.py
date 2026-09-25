import multiprocessing
import os

import pytest

from aiagent.state.redis_state_store import RedisStateStore
from aiagent.state.shared_state import ThreadOwnerRecord


pytestmark = pytest.mark.integration


def _register(url: str, queue) -> None:
    store = RedisStateStore(url, prefix="aiagent:test:v12:process")
    store.register_thread(
        ThreadOwnerRecord(
            thread_id="process-thread",
            user_id="process-user",
            session_id="process-session",
        )
    )
    queue.put(store.list_user_threads("process-user"))


def _clear(url: str, queue) -> None:
    store = RedisStateStore(url, prefix="aiagent:test:v12:process")
    queue.put(store.delete_user_threads("process-user"))


def test_cleanup_is_visible_between_processes():
    url = os.getenv("TEST_REDIS_URL", "")
    if not url:
        pytest.skip("TEST_REDIS_URL is not configured")

    bootstrap = RedisStateStore(url, prefix="aiagent:test:v12:process")
    bootstrap.redis.flushdb()
    queue = multiprocessing.Queue()

    process_a = multiprocessing.Process(target=_register, args=(url, queue))
    process_a.start()
    process_a.join(timeout=20)
    assert process_a.exitcode == 0
    assert queue.get(timeout=2) == ["process-thread"]

    process_b = multiprocessing.Process(target=_clear, args=(url, queue))
    process_b.start()
    process_b.join(timeout=20)
    assert process_b.exitcode == 0
    assert queue.get(timeout=2) == ["process-thread"]
    assert bootstrap.list_user_threads("process-user") == []