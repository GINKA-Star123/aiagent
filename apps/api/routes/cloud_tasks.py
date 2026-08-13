from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.response_utils import error_message_response, ok_response
from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.task_queue import CloudTaskQueue
from cloud.task_view import sanitize_task


router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


class RebuildTaskRequest(BaseModel):
    force_rebuild: bool = True


class DeadLetterTaskRequest(BaseModel):
    reason: str = Field(default="manual_dead_letter", max_length=120)
    error: str = Field(default="Manually moved to dead letter.", max_length=2000)


def _safe_limit(limit: int) -> int:
    return min(max(limit, 1), 200)


def _queue_name(queue: str) -> str:
    normalized = queue.strip()
    return normalized or "default"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


async def _enqueue_rebuild_task(
    *,
    task_type: str,
    force_rebuild: bool,
    unique_key: str,
    queue: str,
):
    queue_name = _queue_name(queue)

    result = await task_queue.enqueue(
        task_type,
        payload={"force_rebuild": force_rebuild},
        queue=queue_name,
        unique_key=unique_key,
        unique_ttl_seconds=3600,
        max_attempts=3,
    )

    return ok_response(
        task_id=result.task_id,
        task_type=task_type,
        queue=queue_name,
        created=result.created,
        status=result.status,
        unique_key=unique_key,
    )


@router.post("/cloud/tasks/knowledge/rebuild")
async def enqueue_knowledge_rebuild(
    req: RebuildTaskRequest,
    queue: str = "default",
    _: None = Depends(require_cloud_admin),
):
    return await _enqueue_rebuild_task(
        task_type="knowledge.rebuild",
        force_rebuild=req.force_rebuild,
        unique_key="knowledge.rebuild",
        queue=queue,
    )


@router.post("/cloud/tasks/vision-characters/rebuild")
async def enqueue_vision_character_rebuild(
    req: RebuildTaskRequest,
    queue: str = "default",
    _: None = Depends(require_cloud_admin),
):
    return await _enqueue_rebuild_task(
        task_type="vision.characters.rebuild",
        force_rebuild=req.force_rebuild,
        unique_key="vision.characters.rebuild",
        queue=queue,
    )


@router.get("/cloud/tasks")
async def list_cloud_tasks(
    queue: str = "default",
    limit: int = 50,
    _: None = Depends(require_cloud_admin),
):
    queue_name = _queue_name(queue)
    safe_limit = _safe_limit(limit)
    tasks = await task_queue.list_tasks(queue=queue_name, limit=safe_limit)

    return ok_response(
        queue=queue_name,
        limit=safe_limit,
        generated_at=_now_iso(),
        tasks=[sanitize_task(task) for task in tasks],
    )


@router.get("/cloud/tasks/dead")
async def list_dead_cloud_tasks(
    queue: str = "default",
    limit: int = 50,
    _: None = Depends(require_cloud_admin),
):
    queue_name = _queue_name(queue)
    safe_limit = _safe_limit(limit)
    tasks = await task_queue.list_dead_tasks(queue=queue_name, limit=safe_limit)

    return ok_response(
        queue=queue_name,
        limit=safe_limit,
        generated_at=_now_iso(),
        tasks=[sanitize_task(task) for task in tasks],
    )


@router.get("/cloud/tasks/summary")
async def cloud_task_summary(
    queue: str = "default",
    _: None = Depends(require_cloud_admin),
):
    queue_name = _queue_name(queue)
    summary = await task_queue.task_summary(queue=queue_name)

    return ok_response(
        queue=queue_name,
        generated_at=_now_iso(),
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
        retried=True,
        task=sanitize_task(task) if task else {},
    )


@router.post("/cloud/tasks/{task_id}/dead-letter")
async def move_cloud_task_to_dead_letter(
    task_id: str,
    req: DeadLetterTaskRequest,
    _: None = Depends(require_cloud_admin),
):
    task = await task_queue.get(task_id)
    if not task:
        return error_message_response(
            stage="cloud_task_dead_letter",
            error="Task not found.",
            status_code=404,
            extra={"task_id": task_id},
        )

    await task_queue.dead_letter(
        task_id,
        req.error,
        reason=req.reason or "manual_dead_letter",
    )
    next_task = await task_queue.get(task_id)

    return ok_response(
        task_id=task_id,
        status="dead",
        dead_lettered=True,
        task=sanitize_task(next_task) if next_task else {},
    )