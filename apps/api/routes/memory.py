# apps/api/routes/memory.py
from __future__ import annotations

from fastapi import APIRouter

from aiagent.schemas.memory import (
    MemoryEditRequest,
    MemoryLayer,
    MemoryMergeRequest,
    MemoryPinRequest,
    MemoryPreferenceUpdate,
)
from apps.api.response_utils import error_message_response, ok_response
from apps.core.runtime_registry import get_runtime

router = APIRouter()


@router.get("/memory/user/{user_id}")
def get_user_memory(user_id: str):
    runtime = get_runtime()
    return ok_response(
        user_id=user_id,
        profile_memories=runtime.get_user_profile_memories(user_id),
        long_term_memories=runtime.get_long_term_memories(user_id, limit=20),
    )


@router.get("/memory/user/{user_id}/snapshot")
def get_user_memory_snapshot(user_id: str, limit: int = 200):
    runtime = get_runtime()
    return ok_response(
        snapshot=runtime.get_memory_snapshot(user_id=user_id, limit=limit),
    )


@router.get("/memory/user/{user_id}/layers/{layer}")
def get_user_memory_layer(user_id: str, layer: MemoryLayer, limit: int = 100):
    runtime = get_runtime()
    return ok_response(
        result=runtime.get_user_memory_layer(
            user_id=user_id,
            layer=layer.value,
            limit=limit,
        )
    )


@router.get("/memory/user/{user_id}/stats")
def get_user_memory_stats(user_id: str):
    runtime = get_runtime()
    return ok_response(
        stats=runtime.get_memory_stats(user_id),
    )


@router.get("/memory/graph/status")
def get_memory_graph_status():
    runtime = get_runtime()
    return ok_response(
        graph=runtime.get_memory_graph_status(),
    )


@router.get("/memory/user/{user_id}/search")
def search_user_memory(
    user_id: str,
    query: str,
    limit: int = 10,
    layer: MemoryLayer | None = None,
):
    runtime = get_runtime()
    return ok_response(
        result=runtime.search_memories(
            user_id=user_id,
            query=query,
            limit=limit,
            layer=layer.value if layer else None,
        )
    )


@router.delete("/memory/user/{user_id}/memories/{memory_id}")
def delete_user_memory_item(user_id: str, memory_id: str):
    runtime = get_runtime()
    result = runtime.delete_user_memory_item(
        user_id=user_id,
        memory_id=memory_id,
    )

    if result.get("status") == "not_found":
        return error_message_response(
            stage="memory_delete",
            error=result.get("reason", "memory not found"),
            status_code=404,
            extra={
                "user_id": user_id,
                "memory_id": memory_id,
            },
        )

    return ok_response(result=result)


@router.delete("/memory/user/{user_id}/layers/{layer}")
def delete_user_memory_layer(user_id: str, layer: MemoryLayer):
    runtime = get_runtime()
    return ok_response(
        result=runtime.delete_user_memory_layer(
            user_id=user_id,
            layer=layer.value,
        )
    )


@router.delete("/memory/user/{user_id}")
def delete_user_memory(user_id: str):
    runtime = get_runtime()
    result = runtime.clear_user_memories(user_id)
    return ok_response(
        result=result,
        user_id=user_id,
    )

@router.get("/memory/user/{user_id}/preferences")
def get_user_memory_preferences(user_id: str):
    runtime = get_runtime()
    return ok_response(
        preferences=runtime.get_user_memory_preference(user_id),
    )


@router.put("/memory/user/{user_id}/preferences")
def update_user_memory_preferences(user_id: str, req: MemoryPreferenceUpdate):
    runtime = get_runtime()
    return ok_response(
        preferences=runtime.set_user_memory_preference(
            user_id=user_id,
            long_term_enabled=req.long_term_enabled,
            reason=req.reason,
        )
    )


@router.patch("/memory/user/{user_id}/memories/{memory_id}")
def edit_user_memory_item(user_id: str, memory_id: str, req: MemoryEditRequest):
    runtime = get_runtime()
    result = runtime.edit_user_memory_item(
        user_id=user_id,
        memory_id=memory_id,
        request=req,
    )

    if result.get("status") == "not_found":
        return error_message_response(
            stage="memory_edit",
            error=result.get("reason", "memory not found"),
            status_code=404,
            extra={"user_id": user_id, "memory_id": memory_id},
        )

    if result.get("status") == "blocked":
        return error_message_response(
            stage="memory_edit",
            error=result.get("reason", "memory blocked by safety filter"),
            status_code=400,
            extra={"user_id": user_id, "memory_id": memory_id, "guard": result.get("guard")},
        )

    return ok_response(result=result)


@router.post("/memory/user/{user_id}/memories/{memory_id}/pin")
def pin_user_memory_item(user_id: str, memory_id: str, req: MemoryPinRequest):
    runtime = get_runtime()
    result = runtime.set_user_memory_pinned(
        user_id=user_id,
        memory_id=memory_id,
        pinned=req.pinned,
        reason=req.reason,
    )

    if result.get("status") == "not_found":
        return error_message_response(
            stage="memory_pin",
            error=result.get("reason", "memory not found"),
            status_code=404,
            extra={"user_id": user_id, "memory_id": memory_id},
        )

    return ok_response(result=result)


@router.delete("/memory/user/{user_id}/memories/{memory_id}/pin")
def unpin_user_memory_item(user_id: str, memory_id: str):
    runtime = get_runtime()
    result = runtime.set_user_memory_pinned(
        user_id=user_id,
        memory_id=memory_id,
        pinned=False,
        reason="user_unpin",
    )

    if result.get("status") == "not_found":
        return error_message_response(
            stage="memory_pin",
            error=result.get("reason", "memory not found"),
            status_code=404,
            extra={"user_id": user_id, "memory_id": memory_id},
        )

    return ok_response(result=result)


@router.post("/memory/user/{user_id}/merge")
def merge_user_memory_items(user_id: str, req: MemoryMergeRequest):
    runtime = get_runtime()
    result = runtime.merge_user_memories(user_id=user_id, request=req)

    if result.get("status") == "not_found":
        return error_message_response(
            stage="memory_merge",
            error=result.get("reason", "memory not found"),
            status_code=404,
            extra={"user_id": user_id, "memory_ids": req.memory_ids},
        )

    if result.get("status") in {"skipped", "blocked"}:
        return error_message_response(
            stage="memory_merge",
            error=result.get("reason", "memory merge failed"),
            status_code=400,
            extra={"user_id": user_id, "memory_ids": req.memory_ids},
        )

    return ok_response(result=result)