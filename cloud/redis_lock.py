from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from cloud.config import cloud_settings
from cloud.redis_client import get_redis_client

_memory_lock = asyncio.Lock()
_memory_locks: dict[str, tuple[str, float]] = {}


@dataclass
class LockLease:
    name: str
    key: str
    token: str
    backend: str
    acquired: bool

    async def release(self) -> None:
        if not self.acquired:
            return

        if self.backend == "redis":
            redis = await get_redis_client()
            if redis is None:
                return

            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            end
            return 0
            """
            await redis.eval(script, 1, self.key, self.token)
            return

        async with _memory_lock:
            current = _memory_locks.get(self.key)
            if current and current[0] == self.token:
                _memory_locks.pop(self.key, None)


class DistributedLock:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    async def acquire(self, name: str, ttl_seconds: int) -> LockLease:
        token = uuid.uuid4().hex
        key = f"{self.prefix}:lock:{name}"

        redis = await get_redis_client()
        if redis is not None:
            ok = await redis.set(key, token, nx=True, ex=ttl_seconds)
            return LockLease(
                name=name,
                key=key,
                token=token,
                backend="redis",
                acquired=bool(ok),
            )

        now = time.time()
        async with _memory_lock:
            current = _memory_locks.get(key)
            if current and current[1] > now:
                return LockLease(name, key, token, "memory", False)

            _memory_locks[key] = (token, now + ttl_seconds)
            return LockLease(name, key, token, "memory", True)


distributed_lock = DistributedLock(prefix=cloud_settings.redis_prefix)
