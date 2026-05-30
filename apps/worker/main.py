from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
import traceback
from typing import Any

from cloud.config import cloud_settings
from cloud.redis_lock import distributed_lock
from cloud.task_queue import CloudTaskQueue
from apps.core.runtime_registry import get_runtime

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("aiagent.worker")

queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)
_stop_event = asyncio.Event()


def _worker_id(index: int) -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{index}"


async def _handle_knowledge_rebuild(payload: dict[str, Any]) -> dict:
    lease = await distributed_lock.acquire("knowledge:rebuild", ttl_seconds=3600)
    if not lease.acquired:
        raise RuntimeError("knowledge rebuild is already running")

    try:
        runtime = get_runtime()
        force_rebuild = bool(payload.get("force_rebuild", True))
        return await asyncio.to_thread(
            runtime.rebuild_knowledge_index,
            force_rebuild=force_rebuild,
        )
    finally:
        await lease.release()


async def _handle_vision_character_rebuild(payload: dict[str, Any]) -> dict:
    lease = await distributed_lock.acquire("vision:characters:rebuild", ttl_seconds=3600)
    if not lease.acquired:
        raise RuntimeError("vision character rebuild is already running")

    try:
        runtime = get_runtime()
        force_rebuild = bool(payload.get("force_rebuild", True))
        return await asyncio.to_thread(
            runtime.rebuild_vision_character_index,
            force_rebuild=force_rebuild,
        )
    finally:
        await lease.release()


async def _run_task(task: dict[str, Any], worker_id: str) -> None:
    task_id = str(task["id"])
    task_type = str(task["type"])
    payload = task.get("payload") or {}

    await queue.start(task_id, worker_id)

    try:
        if task_type == "knowledge.rebuild":
            result = await _handle_knowledge_rebuild(payload)
        elif task_type == "vision.characters.rebuild":
            result = await _handle_vision_character_rebuild(payload)
        else:
            raise RuntimeError(f"unsupported task type: {task_type}")

        await queue.finish(task_id, result)
        logger.info("task succeeded task_id=%s type=%s", task_id, task_type)

    except Exception as exc:
        logger.exception("task failed task_id=%s type=%s", task_id, task_type)
        await queue.fail_or_retry(
            task_id,
            error=f"{exc}\n{traceback.format_exc()}",
        )


async def _worker_loop(index: int) -> None:
    worker_id = _worker_id(index)
    queue_name = os.getenv("TASK_QUEUE_NAME", "default")
    timeout = int(os.getenv("TASK_POP_TIMEOUT_SECONDS", "5"))

    logger.info("worker started worker_id=%s queue=%s", worker_id, queue_name)
    stale_seconds = int(os.getenv("TASK_STALE_SECONDS", "1800"))
    recovered = await queue.recover_stale_running(
        queue=queue_name,
        stale_seconds=stale_seconds,
    )
    if recovered:
        logger.warning(
            "recovered stale running tasks worker_id=%s queue=%s count=%s",
            worker_id,
            queue_name,
            recovered,
        )
    while not _stop_event.is_set():
        task = await queue.pop(queue=queue_name, timeout_seconds=timeout)
        if task is None:
            continue

        await _run_task(task, worker_id)

    logger.info("worker stopped worker_id=%s", worker_id)


def _install_signal_handlers() -> None:
    loop = asyncio.get_running_loop()

    def stop() -> None:
        logger.info("worker shutdown requested")
        _stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop())


async def main() -> None:
    _install_signal_handlers()

    concurrency = int(os.getenv("WORKER_CONCURRENCY", "1"))
    workers = [
        asyncio.create_task(_worker_loop(index))
        for index in range(concurrency)
    ]

    await _stop_event.wait()

    for worker in workers:
        worker.cancel()

    await asyncio.gather(*workers, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())