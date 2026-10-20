from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class CloudTimeoutError(TimeoutError):
    def __init__(self, stage: str, timeout_seconds: float) -> None:
        self.stage = stage
        self.timeout_seconds = timeout_seconds
        super().__init__(f"{stage} timed out after {timeout_seconds}s")


async def run_with_timeout(
    stage: str,
    timeout_seconds: float,
    awaitable: Awaitable[T],
) -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise CloudTimeoutError(stage, timeout_seconds) from exc


async def to_thread_with_timeout(
    stage: str,
    timeout_seconds: float,
    func: Callable[..., T],
    *args,
    **kwargs,
) -> T:
    return await run_with_timeout(
        stage,
        timeout_seconds,
        asyncio.to_thread(func, *args, **kwargs),
    )
