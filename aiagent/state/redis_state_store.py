from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator

from aiagent.state.shared_state import (
    DEFAULT_MAX_THREADS_PER_USER,
    DEFAULT_SESSION_TTL_SECONDS,
    DEFAULT_THREAD_TTL_SECONDS,
    SessionRecord,
    SharedStateConflictError,
    SharedStateOwnershipError,
    SharedStateUnavailableError,
    ThreadOwnerRecord,
    utc_now,
)

logger = logging.getLogger("aiagent.shared_state")


_RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


_FENCED_WRITE_SCRIPT = """
local current = redis.call('get', KEYS[1])
if not current then
    return -1
end
local payload = cjson.decode(current)
if tonumber(payload.fence) ~= tonumber(ARGV[1]) then
    return 0
end
redis.call('set', KEYS[1], ARGV[2], 'EX', ARGV[3])
return 1
"""


class RedisStateStore:
    def __init__(
        self,
        redis_url: str,
        prefix: str = "aiagent:v1",
        *,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        thread_ttl_seconds: int = DEFAULT_THREAD_TTL_SECONDS,
        max_threads_per_user: int = DEFAULT_MAX_THREADS_PER_USER,
        fail_closed: bool = True,
    ) -> None:
        if not redis_url.strip():
            raise ValueError("redis_url must not be empty")
        try:
            from redis import Redis
        except Exception as exc:
            raise SharedStateUnavailableError("redis package is unavailable") from exc

        self.redis = Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
        self.prefix = prefix.rstrip(":")
        self.session_ttl_seconds = session_ttl_seconds
        self.thread_ttl_seconds = thread_ttl_seconds
        self.max_threads_per_user = max_threads_per_user
        self.fail_closed = fail_closed
        self._local = threading.local()

        try:
            self.redis.ping()
        except Exception as exc:
            raise SharedStateUnavailableError("redis ping failed") from exc

    def _key(self, kind: str, value: str) -> str:
        return f"{self.prefix}:v12:{kind}:{value}"

    def _session_key(self, session_id: str) -> str:
        return self._key("session", session_id)

    def _lock_key(self, session_id: str) -> str:
        return self._key("session-lock", session_id)

    def _owner_key(self, thread_id: str) -> str:
        return self._key("thread-owner", thread_id)

    def _user_threads_key(self, user_id: str) -> str:
        return self._key("user-threads", user_id)

    @staticmethod
    def _encode(value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _decode(value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        data = json.loads(value)
        if not isinstance(data, dict):
            raise SharedStateConflictError("shared state payload must be an object")
        return data

    def _raise_unavailable(self, exc: Exception) -> None:
        raise SharedStateUnavailableError("shared state backend is unavailable") from exc

    def ensure_session(self, session_id: str, user_id: str, thread_id: str) -> SessionRecord:
        if not session_id or not user_id or not thread_id:
            raise ValueError("session_id, user_id and thread_id are required")
        key = self._session_key(session_id)
        try:
            with self.redis.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(key)
                        current = self._decode(pipe.get(key)) #type: ignore
                        if current:
                            if current["user_id"] != user_id or current["thread_id"] != thread_id:
                                raise SharedStateOwnershipError("session belongs to another owner")
                            return SessionRecord(**{k: current[k] for k in SessionRecord.__dataclass_fields__})
                        record = SessionRecord(session_id=session_id, user_id=user_id, thread_id=thread_id)
                        pipe.multi()
                        pipe.set(key, self._encode(record.to_dict()), ex=self.session_ttl_seconds)
                        pipe.execute()
                        return record
                    except Exception as exc:
                        if exc.__class__.__name__ == "WatchError":
                            continue
                        raise
        except (SharedStateOwnershipError, SharedStateConflictError):
            raise
        except Exception as exc:
            self._raise_unavailable(exc)
            raise AssertionError("unreachable")

    def register_thread(self, record: ThreadOwnerRecord) -> None:
        try:
            owner_key = self._owner_key(record.thread_id)
            existing = self._decode(self.redis.get(owner_key)) #type: ignore
            if existing and (
                existing["user_id"] != record.user_id
                or existing["session_id"] != record.session_id
            ):
                raise SharedStateOwnershipError("thread belongs to another owner")
            self.redis.set(owner_key, self._encode(record.to_dict()), ex=self.thread_ttl_seconds)
            self.redis.sadd(self._user_threads_key(record.user_id), record.thread_id)
            self.redis.expire(self._user_threads_key(record.user_id), self.thread_ttl_seconds)
            if self.redis.scard(self._user_threads_key(record.user_id)) > self.max_threads_per_user: #type: ignore
                raise SharedStateConflictError("maximum threads per user exceeded")
        except (SharedStateOwnershipError, SharedStateConflictError):
            raise
        except Exception as exc:
            self._raise_unavailable(exc)

    def list_user_threads(self, user_id: str) -> list[str]:
        try:
            return sorted(self.redis.smembers(self._user_threads_key(user_id))) #type: ignore
        except Exception as exc:
            self._raise_unavailable(exc)
            return []

    def list_all_threads(self) -> list[str]:
        """列出共享 owner 索引中的全部线程，供显式全局重置使用。"""
        pattern = f"{self.prefix}:v12:thread-owner:*"
        marker = f"{self.prefix}:v12:thread-owner:"
        try:
            thread_ids: list[str] = []
            for key in self.redis.scan_iter(match=pattern):  # type: ignore
                key_text = str(key)
                if key_text.startswith(marker):
                    thread_ids.append(key_text[len(marker):])
            return sorted(set(thread_ids))
        except Exception as exc:
            self._raise_unavailable(exc)
            return []

    def delete_thread_registration(self, thread_id: str, user_id: str) -> None:
        try:
            owner = self._decode(self.redis.get(self._owner_key(thread_id))) #type: ignore
            if owner and owner["user_id"] != user_id:
                raise SharedStateOwnershipError("cannot delete another user's thread")
            self.redis.delete(self._owner_key(thread_id))
            self.redis.srem(self._user_threads_key(user_id), thread_id)
        except SharedStateOwnershipError:
            raise
        except Exception as exc:
            self._raise_unavailable(exc)

    def get_thread_owner(
        self,
        thread_id: str,
    ) -> ThreadOwnerRecord | None:
        try:
            payload = self._decode(
                self.redis.get(self._owner_key(thread_id)) # type: ignore
            )
            if payload is None:
                return None

            return ThreadOwnerRecord(
                thread_id=str(payload["thread_id"]),
                user_id=str(payload["user_id"]),
                session_id=str(payload["session_id"]),
                created_at=str(payload.get("created_at", "")),
                updated_at=str(payload.get("updated_at", "")),
            )
        except SharedStateConflictError:
            raise
        except Exception as exc:
            self._raise_unavailable(exc)
            return None
        

    @contextmanager
    def session_lock(
        self,
        session_id: str,
        *,
        lease_seconds: int = 60,
    ) -> Generator[int, None, None]:
        token = f"{uuid.uuid4().hex}:{time.time_ns()}"
        key = self._lock_key(session_id)
        acquired = False

        try:
            try:
                if not self.redis.set(key, token, nx=True, ex=lease_seconds):
                    raise SharedStateConflictError(
                        "session is being processed by another worker"
                    )
                fence = int(self.redis.incr(self._key("session-fence", session_id)))
                self._local.lock_token = token
                self._local.lock_key = key
                acquired = True
            except (SharedStateConflictError, SharedStateUnavailableError):
                raise
            except Exception as exc:
                self._raise_unavailable(exc)

            # yield 放在后端异常处理范围之外，确保锁内业务异常原样向上透传。
            yield fence
        finally:
            if acquired:
                try:
                    self.redis.eval(_RELEASE_LOCK_SCRIPT, 1, key, token)
                except Exception:
                    logger.exception("failed to release shared session lock")

    def write_session(self, record: SessionRecord, fence: int) -> None:
        payload = record.to_dict()
        payload["fence"] = fence
        try:
            result = self.redis.eval(
                _FENCED_WRITE_SCRIPT,
                1,
                self._session_key(record.session_id),
                str(fence),
                self._encode(payload),
                str(self.session_ttl_seconds),
            )
            if result == 0:
                raise SharedStateConflictError("stale session fence")
            if result == -1:
                raise SharedStateConflictError("session was deleted during write")
        except SharedStateConflictError:
            raise
        except Exception as exc:
            self._raise_unavailable(exc)

    def get_active_persona_id(
        self,
        scope: str = "global",
    ) -> str | None:
        try:
            value = self.redis.get(
                self._key("persona-active", scope)
            )
            if value is None:
                return None
            return str(value)
        except Exception as exc:
            self._raise_unavailable(exc)
            return None

    def set_active_persona_id(
        self,
        persona_id: str,
        scope: str = "global",
    ) -> None:
        if not persona_id.strip():
            raise ValueError("persona_id must not be empty")

        try:
            self.redis.set(
                self._key("persona-active", scope),
                persona_id,
                ex=self.session_ttl_seconds,
            )
        except Exception as exc:
            self._raise_unavailable(exc) 

    def delete_user_threads(self, user_id: str) -> list[str]:
        thread_ids = self.list_user_threads(user_id)
        for thread_id in thread_ids:
            self.delete_thread_registration(thread_id, user_id)
        return thread_ids

    def health(self) -> dict[str, Any]:
        try:
            self.redis.ping()
            return {"ok": True, "backend": "redis", "prefix": self.prefix}
        except Exception as exc:
            return {"ok": False, "backend": "redis", "error": repr(exc)}
