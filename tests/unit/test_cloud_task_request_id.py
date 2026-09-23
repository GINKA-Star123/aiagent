from __future__ import annotations

import asyncio

from cloud.task_queue import CloudTaskQueue


def test_enqueue_records_request_id_and_first_started_at():
    async def scenario():
        queue = CloudTaskQueue(prefix="unit:request_id")
        submitted = await queue.enqueue(
            "knowledge.rebuild",
            payload={"force_rebuild": False},
            queue="unit",
            request_id="req-abc123",
        )

        task = await queue.get(submitted.task_id)
        assert task["request_id"] == "req-abc123"
        assert task["first_started_at"] in {"", None}

        await queue.start(submitted.task_id, "worker-1")
        started = await queue.get(submitted.task_id)
        assert started["status"] == "running"
        assert started["worker_id"] == "worker-1"
        assert started["attempts"] == 1
        assert started["first_started_at"]
        assert started["started_at"]

        await queue.start(submitted.task_id, "worker-2")
        retried = await queue.get(submitted.task_id)
        assert retried["attempts"] == 2
        assert retried["first_started_at"] == started["first_started_at"]
        assert retried["worker_id"] == "worker-2"

        await queue.finish(submitted.task_id, {"ok": True})
        finished = await queue.get(submitted.task_id)
        assert finished["status"] == "succeeded"
        assert float(finished["duration_ms"]) >= 0.0
        assert finished["request_id"] == "req-abc123"

    asyncio.run(scenario())


def test_enqueue_defaults_request_id_to_empty():
    async def scenario():
        queue = CloudTaskQueue(prefix="unit:request_id_default")
        submitted = await queue.enqueue("vision.characters.rebuild", queue="unit")

        task = await queue.get(submitted.task_id)
        assert task["request_id"] == ""

    asyncio.run(scenario())
