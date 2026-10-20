from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from cloud.config import cloud_settings
from cloud.redis_client import get_redis_client


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int = 0
    backend: str = "memory"


class InMemoryLimitState:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rate: dict[str, tuple[int, float]] = {}
        self._inflight: dict[str, int] = {}

    async def check_rate(self, key: str, limit: int, window_seconds: int) -> LimitDecision:
        now = time.time()
        async with self._lock:
            count, reset_at = self._rate.get(key, (0, now + window_seconds))
            if now >= reset_at:
                count = 0
                reset_at = now + window_seconds

            if count >= limit:
                return LimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=max(1, int(reset_at - now)),
                    backend="memory",
                )

            count += 1
            self._rate[key] = (count, reset_at)
            return LimitDecision(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - count),
                backend="memory",
            )

    async def acquire_inflight(self, key: str, limit: int) -> bool:
        async with self._lock:
            current = self._inflight.get(key, 0)
            if current >= limit:
                return False
            self._inflight[key] = current + 1
            return True

    async def release_inflight(self, key: str) -> None:
        async with self._lock:
            current = self._inflight.get(key, 0)
            if current <= 1:
                self._inflight.pop(key, None)
            else:
                self._inflight[key] = current - 1


_memory_state = InMemoryLimitState()


class RateLimiter:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> LimitDecision:
        redis = await get_redis_client()
        redis_key = f"{self.prefix}:rate:{key}:{int(time.time() // window_seconds)}"

        if redis is None:
            return await _memory_state.check_rate(redis_key, limit, window_seconds)

        try:
            count = await redis.incr(redis_key)
            if count == 1:
                await redis.expire(redis_key, window_seconds + 5)

            if count > limit:
                return LimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=window_seconds,
                    backend="redis",
                )

            return LimitDecision(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - int(count)),
                backend="redis",
            )
        except Exception:
            if cloud_settings.limiter_fail_open:
                return LimitDecision(allowed=True, limit=limit, remaining=limit, backend="fail-open")
            return await _memory_state.check_rate(redis_key, limit, window_seconds)


class ConcurrencyLease:
    def __init__(self, key: str, backend: str, acquired: bool) -> None:
        self.key = key
        self.backend = backend
        self.acquired = acquired
        self._released = False

    async def release(self) -> None:
        if not self.acquired or self._released:
            return

        self._released = True

        if self.backend == "redis":
            redis = await get_redis_client()
            if redis is not None:
                try:
                    await redis.decr(self.key)
                    return
                except Exception:
                    return

        await _memory_state.release_inflight(self.key)


class ConcurrencyLimiter:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    async def acquire(self, key: str, limit: int, lease_seconds: int) -> ConcurrencyLease:
        redis = await get_redis_client()
        redis_key = f"{self.prefix}:inflight:{key}"

        if redis is None:
            acquired = await _memory_state.acquire_inflight(redis_key, limit)
            return ConcurrencyLease(redis_key, "memory", acquired)

        try:
            current = await redis.incr(redis_key)
            if current == 1:
                await redis.expire(redis_key, lease_seconds)

            if int(current) > limit:
                await redis.decr(redis_key)
                return ConcurrencyLease(redis_key, "redis", False)

            return ConcurrencyLease(redis_key, "redis", True)
        except Exception:
            if cloud_settings.limiter_fail_open:
                return ConcurrencyLease(redis_key, "fail-open", True)

            acquired = await _memory_state.acquire_inflight(redis_key, limit)
            return ConcurrencyLease(redis_key, "memory", acquired)
