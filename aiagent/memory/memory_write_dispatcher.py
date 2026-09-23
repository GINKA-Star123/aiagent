from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MemoryWriteDispatcher:
    def __init__(
        self,
        *,
        max_workers: int = 1,
        max_pending: int = 16,
        history_limit: int = 20,
    ) -> None:
        self.max_pending = max(max_pending, 1)
        self.history_limit = max(history_limit, 1)
        # 单线程：记忆写入本身是 IO 密集且要保证顺序（同一用户的多轮写入）。
        self._executor = ThreadPoolExecutor(
            max_workers=max(max_workers, 1),
            thread_name_prefix="memory-write",
        )
        self._condition = threading.Condition()
        self._pending: dict[str, str] = {}
        self._history: deque[dict[str, Any]] = deque(maxlen=self.history_limit)

    def submit(self, fn: Callable[..., Any], /, **kwargs: Any) -> dict[str, Any]:
        """提交一次后台写入。永不抛异常，返回状态字典。"""
        task_id = uuid.uuid4().hex[:12]

        with self._condition:
            if len(self._pending) >= self.max_pending:
                record = {
                    "ok": False,
                    "status": "dropped",
                    "task_id": task_id,
                    "reason": "memory_write_queue_full",
                    "pending": len(self._pending),
                    "created_at": _utc_now(),
                }
                self._history.append(record)
                return dict(record)

            self._pending[task_id] = "queued"
            self._condition.notify_all()

        try:
            self._executor.submit(self._run, task_id, fn, kwargs)
        except Exception as exc:
            with self._condition:
                self._pending.pop(task_id, None)
                self._condition.notify_all()

            record = {
                "ok": False,
                "status": "failed",
                "task_id": task_id,
                "reason": "memory_write_submit_failed",
                "error": str(exc),
                "created_at": _utc_now(),
            }
            self._history.append(record)
            return dict(record)

        return {
            "ok": True,
            "status": "queued",
            "task_id": task_id,
            "reason": "memory_write_queued",
            "created_at": _utc_now(),
        }

    def status(self) -> dict[str, Any]:
        with self._condition:
            pending = len(self._pending)
            recent = [dict(item) for item in list(self._history)[-5:]]

        return {
            "pending": pending,
            "running": pending > 0,
            "max_pending": self.max_pending,
            "last": recent[-1] if recent else {},
            "recent": recent,
        }

    def drain(self, timeout: float = 5.0) -> bool:
        """等待队列排空，供测试与优雅关闭使用。"""
        deadline = time.monotonic() + max(timeout, 0.0)
        with self._condition:
            while self._pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(timeout=remaining)
            return True

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _run(self, task_id: str, fn: Callable[..., Any], kwargs: dict[str, Any]) -> None:
        status = "done"
        error = ""
        try:
            fn(**kwargs)
        except Exception as exc:
            # 记忆写入失败绝不能影响已经发给用户的回复。
            status = "failed"
            error = str(exc)
            logger.warning("Async memory write failed: %s", exc)

        record = {
            "ok": status == "done",
            "status": status,
            "task_id": task_id,
            "reason": "memory_write_finished" if status == "done" else "memory_write_failed",
            "error": error,
            "finished_at": _utc_now(),
        }

        with self._condition:
            self._pending.pop(task_id, None)
            self._history.append(record)
            self._condition.notify_all()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()