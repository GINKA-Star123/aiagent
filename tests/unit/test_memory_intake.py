from aiagent.memory.mem0_memory import MemoryHit
from aiagent.memory.memory_intake import MemoryIntakeService
from aiagent.schemas.memory import MemoryCategory, MemoryImportance, MemoryWriteDecision


def test_memory_intake_allows_safe_new_memory():
    decision = MemoryWriteDecision(
        should_store=True,
        category=MemoryCategory.PREFERENCE,
        importance=MemoryImportance.MEDIUM,
        reason="用户明确表达长期偏好",
        memory_hint="用户喜欢川菜。",
        facts=["用户喜欢川菜。"],
        confidence=0.8,
    )

    plan = MemoryIntakeService().build_store_plan(
        decision=decision,
        memory_hits=[],
        existing_memory_context="无长期记忆。",
        user_text="记住我喜欢川菜",
        assistant_text="好，我记住啦。",
    )

    assert plan.should_store is True
    assert plan.status == "ready"
    assert plan.memory_text == "用户喜欢川菜。"


def test_memory_intake_blocks_secret():
    decision = MemoryWriteDecision(
        should_store=True,
        memory_hint="用户的 API key 是 sk-abcdefghijklmnop",
        facts=["用户的 API key 是 sk-abcdefghijklmnop"],
    )

    plan = MemoryIntakeService().build_store_plan(
        decision=decision,
        memory_hits=[],
        existing_memory_context="无长期记忆。",
        user_text="记住我的 key",
        assistant_text="",
    )

    assert plan.should_store is False
    assert plan.status == "blocked"


def test_memory_intake_skips_duplicate():
    decision = MemoryWriteDecision(
        should_store=True,
        memory_hint="用户喜欢川菜。",
        facts=["用户喜欢川菜。"],
    )

    plan = MemoryIntakeService().build_store_plan(
        decision=decision,
        memory_hits=[
            MemoryHit(
                id="m1",
                memory="用户很喜欢川菜。",
            )
        ],
        existing_memory_context="1. 用户很喜欢川菜。",
        user_text="记住我喜欢川菜",
        assistant_text="好。",
    )

    assert plan.should_store is False
    assert plan.status == "duplicate"