import json

from fastapi import APIRouter, Response

from apps.core.runtime_registry import get_runtime

router = APIRouter()


@router.get("/memory/user/{user_id}")
def get_user_memory(user_id: str):
    runtime = get_runtime()

    body = json.dumps(
        {
            "user_id": user_id,
            "profile_memories": runtime.get_user_profile_memories(user_id),
            "long_term_memories": runtime.get_long_term_memories(user_id, limit=20),
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )


@router.get("/memory/user/{user_id}/stats")
def get_user_memory_stats(user_id: str):
    runtime = get_runtime()
    body = json.dumps(
        {
            "ok": True,
            "stats": runtime.get_memory_stats(user_id),
        },
        ensure_ascii=False,
    )
    return Response(content=body, media_type="application/json; charset=utf-8")


@router.get("/memory/user/{user_id}/search")
def search_user_memory(user_id: str, query: str, limit: int = 10):
    runtime = get_runtime()
    body = json.dumps(
        {
            "ok": True,
            "result": runtime.search_memories(user_id=user_id, query=query, limit=limit),
        },
        ensure_ascii=False,
    )
    return Response(content=body, media_type="application/json; charset=utf-8")


@router.delete("/memory/user/{user_id}")
def delete_user_memory(user_id: str):
    runtime = get_runtime()
    result = runtime.clear_user_memories(user_id)

    body = json.dumps(
        {
            "ok": True,
            "result": result,
            "user_id": user_id,
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )
