from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.response_utils import json_response
from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.ops_snapshot import build_config_snapshot
from cloud.readiness import build_ops_readiness
from cloud.task_queue import CloudTaskQueue

router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


@router.get("/cloud/ops/readiness")
async def readiness(_: None = Depends(require_cloud_admin)):
    snapshot = await build_ops_readiness(task_queue=task_queue)
    return json_response(snapshot.model_dump(mode="json"))


@router.get("/cloud/ops/config-snapshot")
async def config_snapshot(_: None = Depends(require_cloud_admin)):
    return json_response(build_config_snapshot())