from aiagent.schemas.memory import MemoryCategory
from aiagent.services.memory_policy_llm_service import MemoryPolicyLLMService


class _FakeLLMService:
    def invoke_messages(self, *args, **kwargs):
        return '{"should_store": false, "reason": "llm_fallback"}'


def test_memory_policy_rule_based_explicit_preference():
    service = MemoryPolicyLLMService(llm_service=_FakeLLMService())  # type: ignore[arg-type]

    decision = service.decide_write(
        user_text="记住我喜欢川菜，不喜欢甜口。",
        assistant_text="好，我记住啦。",
        existing_memory_context="无长期记忆。",
        planner_should_store_memory=False,
    )

    assert decision.should_store is True
    assert decision.category == MemoryCategory.PREFERENCE
    assert decision.facts
    assert decision.metadata["memory_policy_source"] == "rule_based"