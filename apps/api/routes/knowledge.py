from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.task_queue import CloudTaskQueue
from apps.api.request_context import get_request_id
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

@router.get("/knowledge/index/freshness")
def knowledge_index_freshness(refresh: bool = False):
    runtime = get_runtime()
    body = json.dumps(
        {
            "ok": True,
            "freshness": runtime.get_knowledge_index_freshness(refresh=refresh),
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
    runtime = get_runtime()

    # 云模式：走分布式任务队列，避免多副本重复重建。
    if cloud_settings.cloud_mode:
        task = await task_queue.enqueue(
            "knowledge.rebuild",
            payload={"force_rebuild": req.force_rebuild},
            unique_key="knowledge.rebuild",
            unique_ttl_seconds=3600,
            # 把当前请求的 request_id 带进任务，便于跨进程检索日志。
            request_id=get_request_id(),
        )
        body = {
            "ok": True,
            "mode": "task",
            "task_id": task.task_id,
            "created": task.created,
            "status": task.status,
        }
    # 本地模式 + 要求异步：走进程内后台线程，立即返回，进度看 /knowledge/rebuild/status。
    elif req.async_rebuild:
        body = {
            "ok": True,
            "mode": "async",
            "status": runtime.rebuild_knowledge_index_async(
                force_rebuild=req.force_rebuild,
            ),
        }
    else:
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