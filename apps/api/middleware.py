from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from apps.api.metrics_store import metrics_store
from apps.api.request_context import (
    reset_request_context,
    set_request_context,
)


logger = logging.getLogger("aiagent.api.request")

_REQUEST_ID_PATTERN = re.compile(
    r"^[a-zA-Z0-9._:-]{1,128}$"
)


def normalize_request_id(value: str | None) -> str:
    """
    校验客户端传入的 request_id。

    非法、超长或包含换行等字符时重新生成，
    防止日志注入和异常 Header。
    """

    candidate = (value or "").strip()

    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate

    return uuid.uuid4().hex


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = normalize_request_id(
        request.headers.get("x-request-id")
    )
    method = request.method
    path = request.url.path
    started_at = time.perf_counter()

    context_tokens = set_request_context(
        request_id=request_id,
        method=method,
        path=path,
    )

    try:
        response = await call_next(request)

        latency_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(latency_ms)

        metrics_store.record_request(
            request_id=request_id,
            method=method,
            path=path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )

        logger.info(
            "request completed status_code=%s latency_ms=%s",
            response.status_code,
            latency_ms,
        )

        return response

    except Exception:
        latency_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        metrics_store.record_request(
            request_id=request_id,
            method=method,
            path=path,
            status_code=500,
            latency_ms=latency_ms,
        )

        logger.exception(
            "request failed status_code=500 latency_ms=%s",
            latency_ms,
        )
        raise

    finally:
        reset_request_context(context_tokens)