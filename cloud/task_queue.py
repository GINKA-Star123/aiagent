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

@dataclass(frozen=True)
class TaskFailureResult:
    task_id: str
    status: str
    retried: bool
    dead: bool
    attempts: int
    max_attempts: int
    error: str
    dead_reason: str = ""

class _MemoryTaskStore:
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.unique: dict[str, tuple[str, float]] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.lock = asyncio.Lock()


_memory_store = _MemoryTaskStore()

def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return fallback

def _as_float(value:Any) -> float:
    if value is None:
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0  

    try:
        return float(text)
    except Exception:
        return 0.0

def _duration_ms(started_at: Any, finished_at: Any) -> float:
    started = _as_float(started_at)
    finished = _as_float(finished_at)

    if not started or not finished or finished < started:
        return 0.0

    return round((finished - started) * 1000, 2)


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
        request_id: str = "",
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
                # 发起方的 request_id：worker 日志会带上它，实现跨进程链路检索。
                "request_id": request_id,
                # 首次进入 running 的时间；重试不会覆盖，用于算"任务总时长"。
                "first_started_at": "",
                "worker_id": "",
                "attempts": "0",
                "max_attempts": str(max_attempts),
                "last_error": "",
                "last_failed_at": "",
                "dead_reason": "",
                "last_attempt_started_at": "",
                "last_attempt_finished_at": "",
                "duration_ms": "0",
                "manual_retry_at": "",
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
                "request_id": request_id,
                "first_started_at": None,
                "worker_id": "",
                "attempts": 0,
                "max_attempts": max_attempts,
                "last_error": "",
                "last_failed_at": None,
                "dead_reason": "",
                "last_attempt_started_at": None,
                "last_attempt_finished_at": None,
                "duration_ms": 0.0,
                "manual_retry_at": None,
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
        now_value = time.time()
        now = str(now_value)

        if redis is not None:
            task = await self.get(task_id)
            # 原实现写成 task.get("started_at" or now)：字符串字面量恒为真，
            # 等于始终读 task.get("started_at")，首次启动时是空值。
            started_at = str(task.get("started_at") or now)
            first_started_at = str(task.get("first_started_at") or now)

            await redis.hincrby(self._task_key(task_id), "attempts", 1)
            await redis.hset(
                self._task_key(task_id),
                mapping={
                    "status": "running", 
                    "started_at": started_at, 
                    "first_started_at": first_started_at,
                    "last_attempt_started_at": now,
                    "updated_at": now, 
                    "worker_id": worker_id,
                    "error": "",
                    "dead_reason": "",
                    },
            )
            return

        async with _memory_store.lock:
            task = _memory_store.tasks.get(task_id)
            if task:
                task["attempts"] = int(task.get("attempts", 0)) + 1
                task["status"] = "running"
                task["started_at"] = task.get("started_at") or now_value
                task["first_started_at"] = task.get("first_started_at") or now_value
                task["last_attempt_started_at"] = now_value
                task["updated_at"] = now_value
                task["worker_id"] = worker_id
                task["error"] = ""
                task["dead_reason"] = ""

    async def finish(self, task_id: str, result: Any) -> None:
        task = await self.get(task_id)
        redis = await get_redis_client()
        now_value = time.time()
        now = str(now_value)
        duration = _duration_ms(
            task.get("last_attempt_started_at") or task.get("started_at"),
            now_value,
        )

        if redis is not None:
            await redis.hset(
                self._task_key(task_id),
                mapping={
                    "status": "succeeded",
                    "result": json.dumps(result, ensure_ascii=False, default=str),
                    "error": "",
                    "dead_reason": "",
                    "finished_at": now,
                    "last_attempt_finished_at": now,
                    "updated_at": now,
                    "duration_ms": str(duration),
                },
            )
            await self._release_unique(task)
            return

        async with _memory_store.lock:
            item = _memory_store.tasks.get(task_id)
            if item:
                item["status"] = "succeeded"
                item["result"] = result
                item["error"] = ""
                item["dead_reason"] = ""
                item["finished_at"] = now_value
                item["last_attempt_finished_at"] = now_value
                item["updated_at"] = now_value
                item["duration_ms"] = duration

        await self._release_unique(task)

    
    async def fail_or_retry(self, task_id: str, error: str) -> TaskFailureResult:
        task = await self.get(task_id)
        if not task:
            return TaskFailureResult(
                task_id=task_id,
                status="missing",
                retried=False,
                dead=False,
                attempts=0,
                max_attempts=0,
                error=error,
                dead_reason="task_not_found",
            )

        attempts = _as_int(task.get("attempts"), 0)
        max_attempts = _as_int(task.get("max_attempts"), 3)
        queue = str(task.get("queue") or "default")
        redis = await get_redis_client()
        now_value = time.time()
        now = str(now_value)
        duration = _duration_ms(
            task.get("last_attempt_started_at") or task.get("started_at"),
            now_value,
        )

        if attempts < max_attempts:
            if redis is not None:
                await redis.hset(
                    self._task_key(task_id),
                    mapping={
                        "status": "queued",
                        "error": error,
                        "last_error": error,
                        "last_failed_at": now,
                        "last_attempt_finished_at": now,
                        "updated_at": now,
                        "duration_ms": str(duration),
                    },
                )
                await redis.rpush(self._queue_key(queue), task_id)
            else:
                async with _memory_store.lock:
                    item = _memory_store.tasks.get(task_id)
                    if item:
                        item["status"] = "queued"
                        item["error"] = error
                        item["last_error"] = error
                        item["last_failed_at"] = now_value
                        item["last_attempt_finished_at"] = now_value
                        item["updated_at"] = now_value
                        item["duration_ms"] = duration
                        await _memory_store.queue.put(task_id)

            return TaskFailureResult(
                task_id=task_id,
                status="queued",
                retried=True,
                dead=False,
                attempts=attempts,
                max_attempts=max_attempts,
                error=error,
            )

        dead_reason = "max_attempts_exhausted"
        await self.dead_letter(task_id, error, reason=dead_reason)

        return TaskFailureResult(
            task_id=task_id,
            status="dead",
            retried=False,
            dead=True,
            attempts=attempts,
            max_attempts=max_attempts,
            error=error,
            dead_reason=dead_reason,
        )
    async def dead_letter(
        self,
        task_id: str,
        error: str,
        *,
        reason: str = "max_attempts_exhausted",
    ) -> None:
        task = await self.get(task_id)
        queue = str(task.get("queue") or "default")
        redis = await get_redis_client()
        now_value = time.time()
        now = str(now_value)
        duration = _duration_ms(
            task.get("last_attempt_started_at") or task.get("started_at"),
            now_value,
        )

        if redis is not None:
            await redis.hset(
                self._task_key(task_id),
                mapping={
                    "status": "dead",
                    "error": error,
                    "last_error": error,
                    "last_failed_at": now,
                    "dead_reason": reason,
                    "finished_at": now,
                    "last_attempt_finished_at": now,
                    "updated_at": now,
                    "duration_ms": str(duration),
                },
            )
            await redis.rpush(self._dead_key(queue), task_id)
            await self._release_unique(task)
            return

        async with _memory_store.lock:
            item = _memory_store.tasks.get(task_id)
            if item:
                item["status"] = "dead"
                item["error"] = error
                item["last_error"] = error
                item["last_failed_at"] = now_value
                item["dead_reason"] = reason
                item["finished_at"] = now_value
                item["last_attempt_finished_at"] = now_value
                item["updated_at"] = now_value
                item["duration_ms"] = duration

        await self._release_unique(task)

    
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
                started_at = _as_float(
                    task.get("last_attempt_started_at") or task.get("started_at")
                )
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
                started_at = _as_float(
                    task.get("last_attempt_started_at") or task.get("started_at")
                )
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
        key = self._unique_key(queue, unique_key)

        if redis is not None:
            await redis.delete(key)
            return

        async with _memory_store.lock:
            _memory_store.unique.pop(key, None)

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
        attempts = _as_int(task.get("attempts"), 0)
        max_attempts = _as_int(task.get("max_attempts"), 3)
        next_max_attempts = max(max_attempts, attempts + 1)

        redis = await get_redis_client()
        now_value = time.time()
        now = str(now_value)

        if redis is not None:
            await redis.hset(
                self._task_key(task_id),
                mapping={
                    "status": "queued",
                    "error": "",
                    "dead_reason": "",
                    "finished_at": "",
                    "updated_at": now,
                    "manual_retry_at": now,
                    "max_attempts": str(next_max_attempts),
                },
            )
            await redis.lrem(self._dead_key(queue), 0, task_id)
            await redis.rpush(self._queue_key(queue), task_id)
            return True

        async with _memory_store.lock:
            item = _memory_store.tasks.get(task_id)
            if not item:
                return False

            item["status"] = "queued"
            item["error"] = ""
            item["dead_reason"] = ""
            item["finished_at"] = None
            item["updated_at"] = now_value
            item["manual_retry_at"] = now_value
            item["max_attempts"] = next_max_attempts
            await _memory_store.queue.put(task_id)

        return True

    async def task_summary(self, *, queue: str = "default") -> dict[str, int]:
        tasks = await self.list_tasks(queue=queue, limit=1000)
        depths = await self.queue_depth(queue=queue)

        summary = {
            "queued": 0,
            "running": 0,
            "succeeded": 0,
            "failed": 0,
            "dead": 0,
            "retryable": 0,
            "total": 0,
            "queue_depth": depths["queued"],
            "dead_depth": depths["dead"],
        }

        for task in tasks:
            status = str(task.get("status") or "unknown")
            if status not in summary:
                summary[status] = 0

            summary[status] += 1
            summary["total"] += 1

            if status == "dead":
                summary["retryable"] += 1

        return summary

    async def queue_depth(self, *, queue: str = "default") -> dict[str, int]:
        redis = await get_redis_client()

        if redis is not None:
            queued = await redis.llen(self._queue_key(queue))
            dead = await redis.llen(self._dead_key(queue))
            return {
                "queued": int(queued),
                "dead": int(dead),
            }

        async with _memory_store.lock:
            queued = 0
            dead = 0
            for task in _memory_store.tasks.values():
                if str(task.get("queue") or "default") != queue:
                    continue
                status = str(task.get("status") or "")
                if status == "queued":
                    queued += 1
                elif status == "dead":
                    dead += 1

        return {
            "queued": queued,
            "dead": dead,
        }