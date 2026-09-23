from __future__ import annotations

from typing import Any

from aiagent.schemas.memory import (
    MemoryCategory,
    MemoryImportance,
    MemoryLayer,
    MemoryLayerBucket,
    MemoryRecord,
    MemorySensitivity,
    MemorySnapshot,
)

CATEGORY_TO_LAYER: dict[MemoryCategory, MemoryLayer] = {
    MemoryCategory.IDENTITY: MemoryLayer.PROFILE,
    MemoryCategory.RELATIONSHIP: MemoryLayer.PROFILE,
    MemoryCategory.PREFERENCE: MemoryLayer.PREFERENCE,
    MemoryCategory.HABIT: MemoryLayer.PREFERENCE,
    MemoryCategory.GOAL: MemoryLayer.EPISODE,
    MemoryCategory.EVENT: MemoryLayer.EPISODE,
    MemoryCategory.TOPIC: MemoryLayer.EPISODE,
    MemoryCategory.BOUNDARY: MemoryLayer.BOUNDARY,
    MemoryCategory.OTHER: MemoryLayer.OTHER,
}

IMPORTANCE_RANK: dict[MemoryImportance,int] = {
    MemoryImportance.HIGH: 3,
    MemoryImportance.MEDIUM: 2,
    MemoryImportance.LOW: 1,
}

def infer_memory_layer(
        category: MemoryCategory | str | None = None,
        metadata: dict[str,Any] | None = None
) -> MemoryLayer:
    metadata = metadata or {}

    raw_layer = metadata.get("memory_layer") or metadata.get("layer")
    if raw_layer:
        try:
            return MemoryLayer(str(raw_layer))
        except ValueError:
            pass

    try:
        category_value = category if isinstance(category, MemoryCategory) else MemoryCategory(str(category))
    except Exception:
        category_value = MemoryCategory.OTHER

    return CATEGORY_TO_LAYER.get(category_value, MemoryLayer.OTHER)

def normalize_memory_record(item:dict[str,Any]) -> MemoryRecord:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

    category = _enum_value(
        MemoryCategory,
        metadata.get("category") or metadata.get("memory_category") or item.get("category") or item.get("memory_category"), # type: ignore
        MemoryCategory.OTHER
    )
    importance = _enum_value(
        MemoryImportance,
        metadata.get("importance") or metadata.get("memory_importance") or item.get("importance") or item.get("memory_importance"), # type: ignore
        MemoryImportance.MEDIUM
    )
    sensitivity = _enum_value(
        MemorySensitivity,
        metadata.get("sensitivity") or metadata.get("memory_sensitivity") , # type: ignore
        MemorySensitivity.NONE
    )
    layer = infer_memory_layer(category, metadata)

    memory_text = str(item.get("memory") or item.get("data") or item.get("text") or "").strip()

    pinned = _bool_value(
        metadata.get("pinned") or metadata.get("memory_pinned") or item.get("pinned") or item.get("memory_pinned") # type: ignore
    )

    archived = _bool_value(
        metadata.get("archived") or metadata.get("memory_archived") or item.get("archived") or item.get("memory_archived") # type: ignore
    )

    return MemoryRecord(
        id=str(item.get("id", "")),
        memory=memory_text,
        layer=layer,
        category=category,
        importance=importance,
        score=_optional_float(item.get("score")),
        sensitivity=sensitivity,
        metadata=metadata if isinstance(metadata, dict) else {},
        relations=item.get("relations") or [],
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
        pinned=pinned,
        pinned_at=metadata.get("pinned_at") or metadata.get("memory_pinned_at") or item.get("pinned_at"), # type: ignore
        archived=archived
    )

def build_memory_snapshot(
    *,
    user_id: str,
    agent_id: str,
    records: list[MemoryRecord],
) -> MemorySnapshot:
    buckets: dict[MemoryLayer, list[MemoryRecord]] = {
        layer: [] for layer in MemoryLayer
    }

    for record in records:
        buckets.setdefault(record.layer, []).append(record)

    return MemorySnapshot(
        user_id=user_id,
        agent_id=agent_id,
        total=len(records),
        layers=[
            MemoryLayerBucket(
                layer=layer,
                count=len(items),
                memories=items,
            )
            for layer, items in buckets.items()
        ],
    )

def _enum_value(enum_cls, value:Any, fallback):
    try:
        return enum_cls(str(value))
    except Exception:
        return fallback

def _optional_float(value:Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _bool_value(value: Any) -> bool:
    if isinstance(value,bool):
        return value
    if isinstance(value,str):
        return value.strip().lower() in {"1","true","t","y","yes","on"}
    return bool(value)

def _record_sort_key(record:MemoryRecord) -> tuple[int,int,str]:
    return (
        1 if record.pinned else 0,
        IMPORTANCE_RANK.get(record.importance, 0),
        record.pinned_at or record.updated_at or record.created_at or "",
    )

def sort_memory_records(records:list[MemoryRecord]) -> list[MemoryRecord]:
    return sorted(records,key=_record_sort_key,reverse=True)