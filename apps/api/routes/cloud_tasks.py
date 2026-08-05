from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.response_utils import error_message_response, ok_response
from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.task_queue import CloudTaskQueue
from cloud.task_view import sanitize_task


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

    return ok_response(
        task_id=result.task_id,
        created=result.created,
        status=result.status,
    )


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

    return ok_response(
        task_id=result.task_id,
        created=result.created,
        status=result.status,
    )

@router.get("/cloud/tasks")
async def list_cloud_tasks(
    queue: str = "default",
    limit: int = 50,
    _: None = Depends(require_cloud_admin),
):
    safe_limit = min(max(limit, 1), 200)
    tasks = await task_queue.list_tasks(queue=queue, limit=safe_limit)

    return ok_response(
        queue=queue,
        limit=safe_limit,
        tasks=[sanitize_task(task) for task in tasks],
    )


@router.get("/cloud/tasks/dead")
async def list_dead_cloud_tasks(
    queue: str = "default",
    limit: int = 50,
    _: None = Depends(require_cloud_admin),
):
    safe_limit = min(max(limit, 1), 200)
    tasks = await task_queue.list_dead_tasks(queue=queue, limit=safe_limit)

    return ok_response(
        queue=queue,
        limit=safe_limit,
        tasks=[sanitize_task(task) for task in tasks],
    )

@router.get("/cloud/tasks/summary")
async def cloud_task_summary(
    queue: str = "default",
    _: None = Depends(require_cloud_admin),
):
    summary = await task_queue.task_summary(queue=queue)

    return ok_response(
        queue=queue,
        summary=summary,
    )

@router.get("/cloud/tasks/{task_id}")
async def get_cloud_task(
    task_id: str,
    _: None = Depends(require_cloud_admin),
):
    task = await task_queue.get(task_id)
    if not task:
        return error_message_response(
            stage="cloud_task_get",
            error="Task not found.",
            status_code=404,
            extra={"task_id": task_id},
        )

    return ok_response(
        task=sanitize_task(task),
    )


@router.post("/cloud/tasks/{task_id}/retry")
async def retry_cloud_task(
    task_id: str,
    _: None = Depends(require_cloud_admin),
):
    retried = await task_queue.retry_dead_task(task_id)

    if not retried:
        return error_message_response(
            stage="cloud_task_retry",
            error="Task not found or is not in dead status.",
            status_code=404,
            extra={"task_id": task_id},
        )

    task = await task_queue.get(task_id)

    return ok_response(
        task_id=task_id,
        status="queued",
        task=sanitize_task(task) if task else {},
    )