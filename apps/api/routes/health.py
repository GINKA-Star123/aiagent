from __future__ import annotations

from fastapi import APIRouter

from apps.api.response_utils import json_response, ok_response
from cloud.config import cloud_settings
from cloud.readiness import build_public_readiness, redact_snapshot

router = APIRouter()


@router.get("/live")
def live_check():
    """进程存活探针：只看进程是否还在跑，不做任何依赖检查。"""
    return ok_response(status="alive")


@router.get("/health")
def health_check():
    """基础健康：进程可用 + 当前模式。"""
    return ok_response(
        status="ok",
        cloud_mode=cloud_settings.cloud_mode,
    )


@router.get("/ready")
async def ready_check():
    """流量接入探针：只回可用性信号，不回内部细节。

    需要完整细节（Redis 错误串、GPU 地址、风险清单、失败策略表）请用
    带强认证的 GET /cloud/ops/readiness。
    """
    snapshot = await build_public_readiness()
    return json_response(redact_snapshot(snapshot).model_dump(mode="json"))
