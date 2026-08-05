from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.task_queue import CloudTaskQueue
from apps.core.runtime_registry import get_runtime

router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 4
    include_prompt_context: bool = True
    include_citations: bool = True
    include_confidence: bool = True


class KnowledgeRebuildRequest(BaseModel):
    force_rebuild: bool = True
    async_rebuild: bool = True


@router.get("/knowledge/stats")
def knowledge_stats():
    runtime = get_runtime()
    body = json.dumps(
        {
            "ok": True,
            "stats": runtime.get_knowledge_stats(),
        },
        ensure_ascii=False,
        default=str,
    )
    return Response(content=body, media_type="application/json; charset=utf-8")


@router.get("/knowledge/rebuild/status")
def knowledge_rebuild_status():
    runtime = get_runtime()
    body = json.dumps(
        {
            "ok": True,
            "status": runtime.get_knowledge_rebuild_status(),
        },
        ensure_ascii=False,
        default=str,
    )
    return Response(content=body, media_type="application/json; charset=utf-8")


@router.post("/knowledge/search")
def knowledge_search(req: KnowledgeSearchRequest):
    runtime = get_runtime()

    inspection = runtime.inspect_knowledge(
        query=req.query,
        top_k=req.top_k,
    )

    body = {
        "ok": True,
        "query": req.query,
        "normalized_query": inspection.get("query", req.query),
        "top_k": req.top_k,
        "should_inject": inspection.get("should_inject", False),
        "chunks": inspection.get("chunks", []),
    }

    if req.include_prompt_context:
        body["prompt_context"] = inspection.get("prompt_context", "")

    if req.include_citations:
        body["citations"] = inspection.get("citations", [])

    if req.include_confidence:
        body["confidence"] = inspection.get("confidence", {})

    if "reason" in inspection:
        body["reason"] = inspection["reason"]

    return Response(
        content=json.dumps(body, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
    )


@router.post("/knowledge/rebuild")
async def knowledge_rebuild(
    req: KnowledgeRebuildRequest,
    _: None = Depends(require_cloud_admin),
):
    if cloud_settings.cloud_mode or req.async_rebuild:
        task = await task_queue.enqueue(
            "knowledge.rebuild",
            payload={"force_rebuild": req.force_rebuild},
            unique_key="knowledge.rebuild",
            unique_ttl_seconds=3600,
        )
        body = {
            "ok": True,
            "mode": "task",
            "task_id": task.task_id,
            "created": task.created,
            "status": task.status,
        }
    else:
        runtime = get_runtime()
        body = {
            "ok": True,
            "mode": "sync",
            "stats": runtime.rebuild_knowledge_index(
                force_rebuild=req.force_rebuild,
            ),
        }

    return Response(
        content=json.dumps(body, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
    )