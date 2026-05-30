from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from cloud.config import cloud_settings
from cloud.redis_client import get_redis_client


@dataclass(frozen=True)
class TaskSubmitResult:
    task_id: str
    created: bool
    status: str


class _MemoryTaskStore:
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.unique: dict[str, tuple[str, float]] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.lock = asyncio.Lock()


_memory_store = _MemoryTaskStore()


class CloudTaskQueue:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def _task_key(self, task_id: str) -> str:
        return f"{self.prefix}:task:{task_id}"

    def _queue_key(self, queue: str) -> str:
        return f"{self.prefix}:tasks:queue:{queue}"

    def _dead_key(self, queue: str) -> str:
        return f"{self.prefix}:tasks:dead:{queue}"

    def _unique_key(self, queue: str, unique_key: str) -> str:
        return f"{self.prefix}:tasks:unique:{queue}:{unique_key}"

    async def enqueue(
        self,
        task_type: str,
        payload: dict[str, Any] | None = None,
        *,
        queue: str = "default",
        unique_key: str | None = None,
        unique_ttl_seconds: int = 1800,
        max_attempts: int = 3,
    ) -> TaskSubmitResult:
        payload = payload or {}
        task_id = uuid.uuid4().hex
        now = time.time()

        redis = await get_redis_client()
        if redis is not None:
            if unique_key:
                unique_redis_key = self._unique_key(queue, unique_key)
                ok = await redis.set(unique_redis_key, task_id, nx=True, ex=unique_ttl_seconds)
                if not ok:
                    existing_id = await redis.get(unique_redis_key)
                    if existing_id:
                        existing = await self.get(existing_id)
                        return TaskSubmitResult(
                            task_id=existing_id,
                            created=False,
                            status=str(existing.get("status", "unknown")),
                        )

            record = {
                "id": task_id,
                "type": task_type,
                "queue": queue,
                "status": "queued",
                "payload": json.dumps(payload, ensure_ascii=False),
                "result": "",
                "error": "",
                "unique_key": unique_key or "",
                "created_at": str(now),
                "started_at": "",
                "finished_at": "",
                "updated_at": str(now),
                "worker_id": "",
                "attempts": "0",
                "max_attempts": str(max_attempts),
            }

            await redis.hset(self._task_key(task_id), mapping=record)
            await redis.rpush(self._queue_key(queue), task_id)
            return TaskSubmitResult(task_id=task_id, created=True, status="queued")

        async with _memory_store.lock:
            if unique_key:
                key = self._unique_key(queue, unique_key)
                current = _memory_store.unique.get(key)
                if current and current[1] > now:
                    existing = _memory_store.tasks.get(current[0], {})
                    return TaskSubmitResult(
                        task_id=current[0],
                        created=False,
                        status=str(existing.get("status", "unknown")),
                    )
                _memory_store.unique[key] = (task_id, now + unique_ttl_seconds)

            _memory_store.tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "queue": queue,
                "status": "queued",
                "payload": payload,
                "result": None,
                "error": "",
                "unique_key": unique_key or "",
                "created_at": now,
                "started_at": None,
                "finished_at": None,
                "updated_at": now,
                "worker_id": "",
                "attempts": 0,
                "max_attempts": max_attempts,
            }
            await _memory_store.queue.put(task_id)

        return TaskSubmitResult(task_id=task_id, created=True, status="queued")

    async def get(self, task_id: str) -> dict[str, Any]:
        redis = await get_redis_client()
        if redis is not None:
            data = await redis.hgetall(self._task_key(task_id))
            if not data:
                return {}
            data["payload"] = json.loads(data.get("payload") or "{}")
            data["result"] = json.loads(data.get("result") or "null")
            data["attempts"] = int(data.get("attempts") or 0)
            data["max_attempts"] = int(data.get("max_attempts") or 3)
            return data

        async with _memory_store.lock:
            return dict(_memory_store.tasks.get(task_id, {}))

    async def pop(self, queue: str = "default", timeout_seconds: int = 5) -> dict[str, Any] | None:
        redis = await get_redis_client()
        if redis is not None:
            item = await redis.blpop(self._queue_key(queue), timeout=timeout_seconds)
            if not item:
                return None
            return await self.get(item[1])

        try:
            task_id = await asyncio.wait_for(_memory_store.queue.get(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return None

        async with _memory_store.lock:
            return dict(_memory_store.tasks.get(task_id, {}))

    async def start(self, task_id: str, worker_id: str) -> None:
        redis = await get_redis_client()
        now = str(time.time())

        if redis is not None:
            await redis.hincrby(self._task_key(task_id), "attempts", 1)
            await redis.hset(
                self._task_key(task_id),
                mapping={"status": "running", "started_at": now, "updated_at": now, "worker_id": worker_id},
            )
            return

        async with _memory_store.lock:
            task = _memory_store.tasks.get(task_id)
            if task:
                task["attempts"] = int(task.get("attempts", 0)) + 1
                task["status"] = "running"
                task["started_at"] = time.time()
                task["updated_at"] = time.time()
                task["worker_id"] = worker_id

    async def finish(self, task_id: str, result: Any) -> None:
        task = await self.get(task_id)
        redis = await get_redis_client()
        now = str(time.time())

        if redis is not None:
            await redis.hset(
                self._task_key(task_id),
                mapping={
                    "status": "succeeded",
                    "result": json.dumps(result, ensure_ascii=False, default=str),
                    "finished_at": now,
                    "updated_at": now,
                },
            )
            await self._release_unique(task)
            return

        async with _memory_store.lock:
            item = _memory_store.tasks.get(task_id)
            if item:
                item["status"] = "succeeded"
                item["result"] = result
                item["finished_at"] = time.time()
                item["updated_at"] = time.time()

    async def fail_or_retry(self, task_id: str, error: str) -> None:
        task = await self.get(task_id)
        attempts = int(task.get("attempts") or 0)
        max_attempts = int(task.get("max_attempts") or 3)
        queue = str(task.get("queue") or "default")
        now = str(time.time())

        redis = await get_redis_client()
        if attempts < max_attempts:
            if redis is not None:
                await redis.hset(
                    self._task_key(task_id),
                    mapping={"status": "queued", "error": error, "updated_at": now},
                )
                await redis.rpush(self._queue_key(queue), task_id)
                return

            async with _memory_store.lock:
                item = _memory_store.tasks.get(task_id)
                if item:
                    item["status"] = "queued"
                    item["error"] = error
                    item["updated_at"] = time.time()
                    await _memory_store.queue.put(task_id)
                return

        await self.dead_letter(task_id, error)

    async def dead_letter(self, task_id: str, error: str) -> None:
        task = await self.get(task_id)
        queue = str(task.get("queue") or "default")
        redis = await get_redis_client()
        now = str(time.time())

        if redis is not None:
            await redis.hset(
                self._task_key(task_id),
                mapping={"status": "dead", "error": error, "finished_at": now, "updated_at": now},
            )
            await redis.rpush(self._dead_key(queue), task_id)
            await self._release_unique(task)
            return

        async with _memory_store.lock:
            item = _memory_store.tasks.get(task_id)
            if item:
                item["status"] = "dead"
                item["error"] = error
                item["finished_at"] = time.time()
                item["updated_at"] = time.time()

    async def recover_stale_running(self, queue: str, stale_seconds: int = 1800) -> int:
        redis = await get_redis_client()
        now = time.time()
        recovered = 0

        if redis is not None:
            pattern = f"{self.prefix}:task:*"
            async for key in redis.scan_iter(match=pattern):
                task = await redis.hgetall(key)
                if task.get("queue") != queue or task.get("status") != "running":
                    continue
                started_at = float(task.get("started_at") or 0)
                if started_at and now - started_at > stale_seconds:
                    task_id = str(task["id"])
                    await redis.hset(key, mapping={"status": "queued", "updated_at": str(now)})
                    await redis.rpush(self._queue_key(queue), task_id)
                    recovered += 1
            return recovered

        async with _memory_store.lock:
            for task_id, task in _memory_store.tasks.items():
                if task.get("queue") != queue or task.get("status") != "running":
                    continue
                started_at = float(task.get("started_at") or 0)
                if started_at and now - started_at > stale_seconds:
                    task["status"] = "queued"
                    task["updated_at"] = now
                    await _memory_store.queue.put(task_id)
                    recovered += 1

        return recovered

    async def _release_unique(self, task: dict[str, Any]) -> None:
        unique_key = str(task.get("unique_key") or "")
        queue = str(task.get("queue") or "default")
        if not unique_key:
            return

        redis = await get_redis_client()
        if redis is not None:
            await redis.delete(self._unique_key(queue, unique_key))

    async def list_tasks(
        self,
        *,
        queue: str = "default",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        redis = await get_redis_client()

        if redis is not None:
            pattern = f"{self.prefix}:task:*"
            tasks: list[dict[str, Any]] = []

            async for key in redis.scan_iter(match=pattern):
                task = await redis.hgetall(key)
                if not task:
                    continue
                if str(task.get("queue") or "default") != queue:
                    continue

                task_id = str(task.get("id") or "")
                item = await self.get(task_id)
                if item:
                    tasks.append(item)

            tasks.sort(
                key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0),
                reverse=True,
            )
            return tasks[:limit]

        async with _memory_store.lock:
            tasks = [
                dict(task)
                for task in _memory_store.tasks.values()
                if str(task.get("queue") or "default") == queue
            ]

        tasks.sort(
            key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0),
            reverse=True,
        )
        return tasks[:limit]

    async def list_dead_tasks(
        self,
        *,
        queue: str = "default",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        redis = await get_redis_client()

        if redis is not None:
            ids = await redis.lrange(self._dead_key(queue), -limit, -1)
            ids = list(reversed(ids))
            tasks = []

            for task_id in ids:
                task = await self.get(str(task_id))
                if task:
                    tasks.append(task)

            return tasks

        async with _memory_store.lock:
            tasks = [
                dict(task)
                for task in _memory_store.tasks.values()
                if str(task.get("queue") or "default") == queue
                and str(task.get("status") or "") == "dead"
            ]

        tasks.sort(
            key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0),
            reverse=True,
        )
        return tasks[:limit]

    async def retry_dead_task(self, task_id: str) -> bool:
        task = await self.get(task_id)
        if not task:
            return False

        if str(task.get("status") or "") != "dead":
            return False

        queue = str(task.get("queue") or "default")
        now = str(time.time())

        redis = await get_redis_client()
        if redis is not None:
            await redis.hset(
                self._task_key(task_id),
                mapping={
                    "status": "queued",
                    "error": "",
                    "finished_at": "",
                    "updated_at": now,
                },
            )
            await redis.rpush(self._queue_key(queue), task_id)
            return True

        async with _memory_store.lock:
            item = _memory_store.tasks.get(task_id)
            if not item:
                return False

            item["status"] = "queued"
            item["error"] = ""
            item["finished_at"] = None
            item["updated_at"] = time.time()
            await _memory_store.queue.put(task_id)

        return True

    async def task_summary(self, *, queue: str = "default") -> dict[str, int]:
        tasks = await self.list_tasks(queue=queue, limit=1000)

        summary = {
            "queued": 0,
            "running": 0,
            "succeeded": 0,
            "failed": 0,
            "dead": 0,
            "total": 0,
        }

        for task in tasks:
            status = str(task.get("status") or "unknown")
            if status not in summary:
                summary[status] = 0
            summary[status] += 1
            summary["total"] += 1

        return summary