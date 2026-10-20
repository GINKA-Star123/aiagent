from __future__ import annotations

import logging
from typing import Any

from cloud.config import cloud_settings

logger = logging.getLogger("aiagent.cloud.redis")

_redis_client:Any|None = None

async def get_redis_client() ->Any |None:
    global _redis_client

    if not cloud_settings.redis_url:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        from redis.asyncio import from_url
    except Exception as exc:
        logger.warning("Redis module is not found: %s",exc)
        return None

    try:
        _redis_client = from_url(
            cloud_settings.redis_url,
            encoding = "utf-8",
            decode_responses=True,
            socket_connect_timeout = 2,
            socket_timeout = 2,
            health_check_interval = 30,
        )
        await _redis_client.ping()
        return _redis_client
    except Exception as exc:
        logger.warning("Redis is unavailable %s",exc)
        _redis_client=None
        return _redis_client

async def redis_health() ->dict[str,object]:
    client = await get_redis_client()
    if client is None:
        return {"ok":False,"enabled":bool(cloud_settings.redis_url)}

    try:
        await client.ping()
        return {"ok":True,"enabled":True}

    except Exception as exc:
        return {"ok":False,"enabled":True,"errors":str(exc)}
