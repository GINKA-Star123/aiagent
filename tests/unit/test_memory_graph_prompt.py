from aiagent.graphs.memory_graph import MemoryRunner
from aiagent.memory.mem0_memory import MemoryHit
from aiagent.memory.memory_prompt import MemoryPromptBuilder
from aiagent.schemas.memory import MemoryCategory, MemoryImportance, MemoryLayer, MemoryRecord


class _FakeMemory:
    def search(self, query, user_id, agent_id="yzl", limit=6):
        return [
            MemoryHit(
                id="h1",
                memory="用户喜欢川菜。",
                score=0.88,
                metadata={
                    "category": "preference",
                    "importance": "medium",
                    "memory_layer": "preference",
                },
            )
        ]

    def list_pinned_records(self, user_id, agent_id="yzl", limit=8):
        return [
            MemoryRecord(
                id="p1",
                memory="用户希望被称呼为小张。",
                layer=MemoryLayer.PROFILE,
                category=MemoryCategory.IDENTITY,
                importance=MemoryImportance.HIGH,
                pinned=True,
            )
        ]

    def format_for_prompt(self, hits):
        return "legacy should not be used"


class _FakePolicy:
    pass


def test_memory_runner_retrieve_builds_compressed_prompt_with_pinned_memory():
    runner = MemoryRunner(
        memory=_FakeMemory(),  # type: ignore[arg-type]
        policy_service=_FakePolicy(),  # type: ignore[arg-type]
        prompt_builder=MemoryPromptBuilder(
            max_chars=800,
            pinned_limit=4,
            relevant_limit=6,
            item_max_chars=100,
        ),
    )

    state = runner.retrieve_before_reply(
        user_id="u1",
        user_text="我今天想吃什么？",
        retrieval_query="吃饭偏好",
    )

    assert "用户希望被称呼为小张" in state["memory_prompt_context"]
    assert "用户喜欢川菜" in state["memory_prompt_context"]
    assert state["metadata"]["memory_prompt_compressed"] is True
    assert state["metadata"]["memory_pinned_count"] == 1
    assert state["metadata"]["memory_prompt_layer_counts"]["profile"] == 1
    assert state["metadata"]["memory_prompt_selected_layers"][0] == "profile"
    assert state["metadata"]["memory_prompt_compression_reason"] in {"layered_compact", "char_limit"}
    assert state["memory_prompt_context_data"]["compression_reason"] == state["metadata"]["memory_prompt_compression_reason"]