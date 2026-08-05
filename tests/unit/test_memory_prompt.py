from aiagent.memory.mem0_memory import MemoryHit
from aiagent.memory.memory_prompt import MemoryPromptBuilder
from aiagent.schemas.memory import (
    MemoryCategory,
    MemoryImportance,
    MemoryLayer,
    MemoryPromptSource,
    MemoryRecord,
)


def test_memory_prompt_prioritizes_pinned_records():
    builder = MemoryPromptBuilder(
        max_chars=800,
        pinned_limit=2,
        relevant_limit=2,
        item_max_chars=80,
    )

    context = builder.build(
        pinned_records=[
            MemoryRecord(
                id="p1",
                memory="用户希望被称呼为小张。",
                layer=MemoryLayer.PROFILE,
                category=MemoryCategory.IDENTITY,
                importance=MemoryImportance.HIGH,
                pinned=True,
            )
        ],
        hits=[
            MemoryHit(
                id="h1",
                memory="用户喜欢川菜。",
                score=0.91,
                metadata={
                    "category": "preference",
                    "importance": "medium",
                    "memory_layer": "preference",
                },
            )
        ],
    )

    assert context.pinned_count == 1
    assert context.retrieved_count == 1
    assert "【置顶记忆】" in context.text
    assert "用户希望被称呼为小张" in context.text
    assert "用户喜欢川菜" in context.text
    assert context.items[0].source == MemoryPromptSource.PINNED


def test_memory_prompt_dedupes_pinned_and_retrieved_same_memory():
    builder = MemoryPromptBuilder(
        max_chars=800,
        pinned_limit=4,
        relevant_limit=6,
        item_max_chars=80,
    )

    context = builder.build(
        pinned_records=[
            MemoryRecord(
                id="m1",
                memory="用户喜欢川菜。",
                layer=MemoryLayer.PREFERENCE,
                category=MemoryCategory.PREFERENCE,
                importance=MemoryImportance.MEDIUM,
                pinned=True,
            )
        ],
        hits=[
            MemoryHit(
                id="m1",
                memory="用户喜欢川菜。",
                score=0.95,
                metadata={
                    "category": "preference",
                    "importance": "medium",
                    "memory_layer": "preference",
                    "pinned": True,
                },
                pinned=True,
            )
        ],
    )

    assert context.total_count == 1
    assert context.pinned_count == 1
    assert context.text.count("用户喜欢川菜") == 1


def test_memory_prompt_truncates_to_max_chars():
    builder = MemoryPromptBuilder(
        max_chars=360,
        pinned_limit=2,
        relevant_limit=10,
        item_max_chars=60,
    )

    hits = [
        MemoryHit(
            id=f"h{i}",
            memory=f"用户有一条很长的偏好记忆 {i}，这条记忆用于测试 prompt 压缩和截断行为。",
            score=0.9 - i * 0.01,
            metadata={
                "category": "preference",
                "importance": "medium",
                "memory_layer": "preference",
            },
        )
        for i in range(20)
    ]

    context = builder.build(hits=hits)

    assert context.char_count <= 360
    assert context.truncated is True
    assert "长期记忆摘要" in context.text

def test_memory_prompt_keeps_pinned_first_and_groups_layers():
    builder = MemoryPromptBuilder(max_chars=800, pinned_limit=2, relevant_limit=4, item_max_chars=80)

    context = builder.build(
        pinned_records=[
            MemoryRecord(
                id="p1",
                memory="用户希望被称呼为小张",
                layer=MemoryLayer.PROFILE,
                category=MemoryCategory.IDENTITY,
                importance=MemoryImportance.HIGH,
                pinned=True,
            )
        ],
        hits=[
            MemoryHit(
                id="h1",
                memory="用户喜欢川菜",
                score=0.95,
                metadata={"category": "preference", "importance": "medium", "memory_layer": "preference"},
            ),
            MemoryHit(
                id="h2",
                memory="用户不希望被打断",
                score=0.90,
                metadata={"category": "boundary", "importance": "high", "memory_layer": "boundary"},
            ),
        ],
    )

    assert context.items[0].source == MemoryPromptSource.PINNED
    assert context.selected_layers[0] == "profile"
    assert context.layer_counts["profile"] == 1