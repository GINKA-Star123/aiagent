import asyncio

from cloud.limits import RateLimiter


async def _check_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(prefix="test")
    key = "unit:user"

    first = await limiter.check(key, limit=1, window_seconds=60)
    second = await limiter.check(key, limit=1, window_seconds=60)

    assert first.allowed is True
    assert second.allowed is False


def test_rate_limiter_blocks_after_limit():
    asyncio.run(_check_rate_limiter_blocks_after_limit())
