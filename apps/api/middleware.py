from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from apps.api.request_context import clear_request_context, set_request_context
from apps.api.metrics_store import metrics_store

logger = logging.getLogger("aiagent.api.request")


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    started = time.perf_counter()

    set_request_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        logger.exception(
            "request failed request_id=%s method=%s path=%s latency_ms=%s",
            request_id,
            request.method,
            request.url.path,
            latency_ms,
        )
        raise
    finally:
        clear_request_context()

    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    response.headers["x-request-id"] = request_id
    response.headers["x-response-time-ms"] = str(latency_ms)

    metrics_store.record_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )

    logger.info(
        "request completed request_id=%s method=%s path=%s status_code=%s latency_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )

    return response
