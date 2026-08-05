from aiagent.memory.mem0_memory import MemoryHit
from aiagent.memory.memory_deduper import MemoryDeduper


def test_memory_deduper_detects_similar_existing_hit():
    deduper = MemoryDeduper()
    result = deduper.check(
        candidate="用户喜欢川菜",
        hits=[
            MemoryHit(
                id="m1",
                memory="用户很喜欢川菜。",
            )
        ],
    )

    assert result.duplicate is True
    assert result.matched_memory_id == "m1"


def test_memory_deduper_allows_new_fact():
    deduper = MemoryDeduper()
    result = deduper.check(
        candidate="用户喜欢晚上写代码",
        hits=[
            MemoryHit(
                id="m1",
                memory="用户喜欢川菜。",
            )
        ],
    )

    assert result.duplicate is False