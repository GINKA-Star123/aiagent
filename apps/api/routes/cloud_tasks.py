from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.task_queue import CloudTaskQueue

router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


class RebuildTaskRequest(BaseModel):
    force_rebuild: bool = True


@router.post("/cloud/tasks/knowledge/rebuild")
async def enqueue_knowledge_rebuild(
    req: RebuildTaskRequest,
    _: None = Depends(require_cloud_admin),
):
    result = await task_queue.enqueue(
        "knowledge.rebuild",
        payload={"force_rebuild": req.force_rebuild},
        unique_key="knowledge.rebuild",
        unique_ttl_seconds=3600,
        max_attempts=3,
    )

    return {
        "ok": True,
        "task_id": result.task_id,
        "created": result.created,
        "status": result.status,
    }


@router.post("/cloud/tasks/vision-characters/rebuild")
async def enqueue_vision_character_rebuild(
    req: RebuildTaskRequest,
    _: None = Depends(require_cloud_admin),
):
    result = await task_queue.enqueue(
        "vision.characters.rebuild",
        payload={"force_rebuild": req.force_rebuild},
        unique_key="vision.characters.rebuild",
        unique_ttl_seconds=3600,
        max_attempts=3,
    )

    return {
        "ok": True,
        "task_id": result.task_id,
        "created": result.created,
        "status": result.status,
    }


@router.get("/cloud/tasks/{task_id}")
async def get_cloud_task(
    task_id: str,
    _: None = Depends(require_cloud_admin),
):
    task = await task_queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    return {
        "ok": True,
        "task": task,
    }