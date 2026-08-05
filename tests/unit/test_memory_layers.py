# tests/unit/test_memory_layers.py
from __future__ import annotations

from aiagent.memory.memory_layers import (
    build_memory_snapshot,
    infer_memory_layer,
    normalize_memory_record,
)
from aiagent.schemas.memory import MemoryCategory, MemoryLayer


def test_infer_memory_layer_from_category():
    assert infer_memory_layer(MemoryCategory.IDENTITY) == MemoryLayer.PROFILE
    assert infer_memory_layer(MemoryCategory.RELATIONSHIP) == MemoryLayer.PROFILE
    assert infer_memory_layer(MemoryCategory.PREFERENCE) == MemoryLayer.PREFERENCE
    assert infer_memory_layer(MemoryCategory.HABIT) == MemoryLayer.PREFERENCE
    assert infer_memory_layer(MemoryCategory.GOAL) == MemoryLayer.EPISODE
    assert infer_memory_layer(MemoryCategory.EVENT) == MemoryLayer.EPISODE
    assert infer_memory_layer(MemoryCategory.BOUNDARY) == MemoryLayer.BOUNDARY
    assert infer_memory_layer(MemoryCategory.OTHER) == MemoryLayer.OTHER


def test_infer_memory_layer_prefers_metadata_override():
    layer = infer_memory_layer(
        MemoryCategory.OTHER,
        metadata={"memory_layer": "preference"},
    )

    assert layer == MemoryLayer.PREFERENCE


def test_normalize_memory_record_from_mem0_item():
    record = normalize_memory_record(
        {
            "id": "m1",
            "memory": "用户喜欢川菜。",
            "score": 0.82,
            "metadata": {
                "category": "preference",
                "importance": "high",
            },
            "created_at": "2026-08-03T00:00:00",
        }
    )

    assert record.id == "m1"
    assert record.memory == "用户喜欢川菜。"
    assert record.layer == MemoryLayer.PREFERENCE
    assert record.category == MemoryCategory.PREFERENCE
    assert record.importance == "high"
    assert record.score == 0.82


def test_build_memory_snapshot_keeps_stable_layers():
    records = [
        normalize_memory_record(
            {
                "id": "m1",
                "memory": "用户喜欢川菜。",
                "metadata": {"category": "preference"},
            }
        ),
        normalize_memory_record(
            {
                "id": "m2",
                "memory": "用户希望被称呼为小张。",
                "metadata": {"category": "identity"},
            }
        ),
    ]

    snapshot = build_memory_snapshot(
        user_id="u1",
        agent_id="yzl",
        records=records,
    )

    assert snapshot.user_id == "u1"
    assert snapshot.total == 2

    by_layer = {bucket.layer: bucket for bucket in snapshot.layers}
    assert by_layer[MemoryLayer.PREFERENCE].count == 1
    assert by_layer[MemoryLayer.PROFILE].count == 1
    assert MemoryLayer.BOUNDARY in by_layer