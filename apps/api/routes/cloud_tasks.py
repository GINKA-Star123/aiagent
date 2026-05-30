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


@router.get("/cloud/tasks")
async def list_cloud_tasks(
    queue: str = "default",
    limit: int = 50,
    _: None = Depends(require_cloud_admin),
):
    tasks = await task_queue.list_tasks(queue=queue, limit=limit)

    return {
        "ok": True,
        "queue": queue,
        "tasks": tasks,
    }


@router.get("/cloud/tasks/dead")
async def list_dead_cloud_tasks(
    queue: str = "default",
    limit: int = 50,
    _: None = Depends(require_cloud_admin),
):
    tasks = await task_queue.list_dead_tasks(queue=queue, limit=limit)

    return {
        "ok": True,
        "queue": queue,
        "tasks": tasks,
    }


@router.get("/cloud/tasks/summary")
async def cloud_task_summary(
    queue: str = "default",
    _: None = Depends(require_cloud_admin),
):
    summary = await task_queue.task_summary(queue=queue)

    return {
        "ok": True,
        "queue": queue,
        "summary": summary,
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


@router.post("/cloud/tasks/{task_id}/retry")
async def retry_cloud_task(
    task_id: str,
    _: None = Depends(require_cloud_admin),
):
    retried = await task_queue.retry_dead_task(task_id)

    if not retried:
        raise HTTPException(status_code=404, detail="Task not found or is not in dead status")

    return {
        "ok": True,
        "task_id": task_id,
        "status": "queued",
    }
