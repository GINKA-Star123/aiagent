from __future__ import annotations

import time

from aiagent.memory.memory_write_audit import MemoryWriteAuditLog
from aiagent.memory.memory_write_dispatcher import MemoryWriteDispatcher
from aiagent.schemas.memory import MemoryWriteAudit


def test_dispatcher_runs_task_and_swallows_failure():
    dispatcher = MemoryWriteDispatcher(max_workers=1, max_pending=4)
    seen: list[str] = []

    queued = dispatcher.submit(lambda **kwargs: seen.append(kwargs["name"]), name="first")
    assert queued["status"] == "queued"
    assert dispatcher.drain(timeout=5.0) is True
    assert seen == ["first"]
    assert dispatcher.status()["last"]["status"] == "done"

    dispatcher.submit(lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    assert dispatcher.drain(timeout=5.0) is True
    last = dispatcher.status()["last"]
    assert last["status"] == "failed"
    assert "boom" in last["error"]
    dispatcher.shutdown(wait=True)


def test_dispatcher_drops_when_queue_full():
    dispatcher = MemoryWriteDispatcher(max_workers=1, max_pending=1)
    dispatcher.submit(lambda **kwargs: time.sleep(0.3))

    dropped = dispatcher.submit(lambda **kwargs: None)
    assert dropped["status"] == "dropped"
    assert dropped["reason"] == "memory_write_queue_full"

    assert dispatcher.drain(timeout=5.0) is True
    dispatcher.shutdown(wait=True)


def test_audit_log_append_tail_clear(tmp_path):
    log = MemoryWriteAuditLog(path=tmp_path / "audit.jsonl")

    for index in range(3):
        log.append(
            MemoryWriteAudit(
                audit_id=f"a{index}",
                user_id="u1" if index < 2 else "u2",
                status="stored",
            )
        )

    assert log.count() == 3
    assert log.count(user_id="u1") == 2

    tail = log.tail(user_id="u1", limit=5)
    assert [item.audit_id for item in tail] == ["a1", "a0"]
    assert all(item.created_at for item in tail)

    assert log.clear() == 3
    assert log.count() == 0