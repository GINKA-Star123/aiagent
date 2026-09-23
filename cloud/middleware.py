from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.responses import JSONResponse

from cloud.config import cloud_settings
from cloud.limits import ConcurrencyLimiter, RateLimiter

from apps.api.http_security import (
    build_trusted_proxy_policy,
    resolve_client_ip,
)
from apps.api.middleware import normalize_request_id
from apps.api.request_context import get_request_id
from config.settings import settings

logger = logging.getLogger("aiagent.cloud.middleware")

_rate_limiter = RateLimiter(prefix=cloud_settings.redis_prefix)
_concurrency_limiter = ConcurrencyLimiter(prefix=cloud_settings.redis_prefix)

_trusted_proxy_policy = build_trusted_proxy_policy(
    settings.api_trusted_proxies,
)

_BYPASS_PATHS = {
    "/",
    "/health",
    "/cloud/ready",
    "/cloud/limits",
}


def _route_bucket(path: str) -> str:
    if path == "/chat":
        return "chat"
    if path.startswith("/multimodal"):
        return "multimodal"
    if path.startswith("/voice"):
        return "voice"
    if path == "/knowledge/rebuild":
        return "knowledge_rebuild"
    return "default"


def _rate_limit_for_bucket(bucket: str) -> int:
    if bucket == "chat":
        return cloud_settings.rate_limit_chat_per_minute
    if bucket == "multimodal":
        return cloud_settings.rate_limit_multimodal_per_minute
    if bucket == "voice":
        return cloud_settings.rate_limit_voice_per_minute
    if bucket == "knowledge_rebuild":
        return cloud_settings.rate_limit_rebuild_per_minute
    return cloud_settings.rate_limit_default_per_minute


def _inflight_limit_for_bucket(bucket: str) -> int | None:
    if bucket == "chat":
        return cloud_settings.chat_inflight_limit
    if bucket == "multimodal":
        return cloud_settings.multimodal_inflight_limit
    if bucket == "voice":
        return cloud_settings.voice_inflight_limit
    if bucket == "knowledge_rebuild":
        return cloud_settings.rebuild_inflight_limit
    return None


def _client_identity(request: Request) -> str:
    """
    生成限流身份。

    优先使用 Authorization 的不可逆 Hash。
    未认证请求使用安全解析后的客户端 IP。

    不再信任 X-User-ID，因为普通客户端可以任意伪造该 Header，
    通过不断修改 user id 绕过限流。
    """

    authorization = request.headers.get(
        "authorization"
    )

    if authorization:
        digest = hashlib.sha256(
            authorization.encode("utf-8")
        ).hexdigest()[:24]

        return f"auth:{digest}"

    peer_address = (
        request.client.host
        if request.client
        else None
    )

    client_ip = resolve_client_ip(
        peer_address=peer_address,
        forwarded_for=request.headers.get(
            "x-forwarded-for"
        ),
        trusted_proxies=_trusted_proxy_policy,
    )

    return f"ip:{client_ip}"


def _limit_response(
    *,
    status_code: int,
    request_id: str,
    stage: str,
    message: str,
    retry_after_seconds: int,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "stage": stage,
            "error": message,
            "retry_after_seconds": retry_after_seconds,
            "request_id": request_id,
        },
    )
    response.headers["x-request-id"] = request_id
    response.headers["retry-after"] = str(retry_after_seconds)
    return response


async def cloud_guard_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.url.path in _BYPASS_PATHS:
        return await call_next(request)

    if not cloud_settings.cloud_mode and not cloud_settings.rate_limit_enabled and not cloud_settings.inflight_limit_enabled:
        return await call_next(request)

    request_id = (
        get_request_id()
        or normalize_request_id(
            request.headers.get("x-request-id")
        )
    )
    bucket = _route_bucket(request.url.path)
    identity = _client_identity(request)

    if cloud_settings.rate_limit_enabled:
        limit = _rate_limit_for_bucket(bucket)
        decision = await _rate_limiter.check(
            key=f"{bucket}:{identity}",
            limit=limit,
            window_seconds=60,
        )
        if not decision.allowed:
            return _limit_response(
                status_code=429,
                request_id=request_id,
                stage="rate_limit",
                message="request rate limit exceeded",
                retry_after_seconds=decision.retry_after_seconds,
            )

    global_lease = None
    route_lease = None

    try:
        if cloud_settings.inflight_limit_enabled:
            global_lease = await _concurrency_limiter.acquire(
                key="global",
                limit=cloud_settings.global_inflight_limit,
                lease_seconds=cloud_settings.inflight_lease_seconds,
            )
            if not global_lease.acquired:
                return _limit_response(
                    status_code=503,
                    request_id=request_id,
                    stage="global_concurrency_limit",
                    message="server is busy",
                    retry_after_seconds=3,
                )

            route_limit = _inflight_limit_for_bucket(bucket)
            if route_limit is not None:
                route_lease = await _concurrency_limiter.acquire(
                    key=bucket,
                    limit=route_limit,
                    lease_seconds=cloud_settings.inflight_lease_seconds,
                )
                if not route_lease.acquired:
                    return _limit_response(
                        status_code=503,
                        request_id=request_id,
                        stage="route_concurrency_limit",
                        message=f"{bucket} worker pool is busy",
                        retry_after_seconds=5,
                    )

        response = await call_next(request)
        response.headers["x-cloud-route-bucket"] = bucket
        return response

    finally:
        if route_lease is not None:
            await route_lease.release()
        if global_lease is not None:
            await global_lease.release()