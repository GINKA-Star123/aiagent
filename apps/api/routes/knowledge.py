import json

from fastapi import APIRouter,Response
from pydantic import BaseModel

from apps.core.runtime_registry import get_runtime

router =APIRouter()


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 4
    include_prompt_context : bool = True

class KnowledgeRebuildRequest(BaseModel):
    force_rebuild: bool = True

@router.get("/knowledge/stats")
def knowledge_stats():
    runtime = get_runtime()
    body = json.dumps(
        {
            "ok": True,
            "stats": runtime.get_knowledge_stats(),
        },
        ensure_ascii=False,
    )
    return Response(content=body,media_type="application/json; charset=utf-8")

@router.post("/knowledge/search")
def knowledge_search(req: KnowledgeSearchRequest):
    runtime = get_runtime()
    chunks = runtime.search_knowledge(
        query=req.query,
        top_k=req.top_k,
    )

    body = {
        "ok": True,
        "query": req.query,
        "top_k": req.top_k,
        "chunks": chunks,
    }

    if req.include_prompt_context:
        body["prompt_context"] = runtime.get_knowledge_prompt_context(
            query=req.query,
            top_k=req.top_k,
        )

    body = json.dumps(body,ensure_ascii=False)
    return Response(content=body,media_type="application/json; charset=utf-8")


@router.post("/knowledge/rebuild")
def knowledge_rebuild(req: KnowledgeRebuildRequest):
    runtime = get_runtime()
    stats = runtime.rebuild_knowledge_index(force_rebuild=req.force_rebuild)

    return Response(
        content = json.dumps(
            {
                "ok": True,
                "stats": stats
            },
            ensure_ascii=False
        )
        ,media_type="application/json; charset=utf-8"
    )