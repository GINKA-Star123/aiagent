from __future__ import annotations

from fastapi import APIRouter

from apps.api.response_utils import json_response, ok_response
from cloud.config import cloud_settings
from cloud.readiness import build_public_readiness

router = APIRouter()


@router.get("/live")
def live_check():
    return ok_response(status="alive")


@router.get("/health")
def health_check():
    return ok_response(
        status="ok",
        cloud_mode=cloud_settings.cloud_mode,
    )


@router.get("/ready")
async def ready_check():
    snapshot = await build_public_readiness()
    return json_response(snapshot.model_dump(mode="json"))