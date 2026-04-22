from __future__ import annotations

from aiagent.cognition.state_analyzer import StateAnalyzer
from aiagent.cognition.state_normalizer import StateNormalizer
from aiagent.graphs.state_graph import StateRunner
from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.services.state_llm_service import StateLLMService
from config.settings import settings


def build_persona_runtime() -> PersonaRuntime:
    loader = PersonaLoader(base_dir="data/characters")
    config = loader.load_persona("yzl")
    return PersonaRuntime(config)


def build_state_runner() -> StateRunner:
    state_llm_service = StateLLMService(settings=settings)
    state_analyzer = StateAnalyzer(llm_service=state_llm_service)
    state_normalizer = StateNormalizer()

    return StateRunner(
        state_analyzer=state_analyzer,
        state_normalizer=state_normalizer,
    )


def main() -> None:
    persona_runtime = build_persona_runtime()
    runner = build_state_runner()

    test_cases = [
        {
            "user_text": "阿绫，下午好呀。",
            "user_name": "小花",
            "history": [],
        },
        {
            "user_text": "我明天考试，有点紧张。",
            "user_name": "小花",
            "history": ["阿绫下午好", "最近复习得有点乱"],
        },
        {
            "user_text": "你觉得音乐最吸引人的地方是什么？",
            "user_name": "小花",
            "history": ["我最近在单曲循环一首歌"],
        },
        {
            "user_text": "记住，我最喜欢摇滚。",
            "user_name": "小花",
            "history": [],
        },
    ]

    print("=== PERSONA SUMMARY ===")
    print(persona_runtime.summary())
    print()

    for index, case in enumerate(test_cases, start=1):
        print(f"=== STATE GRAPH TEST {index} ===")
        print("INPUT:")
        print(case)
        print()

        result = runner.run(
            user_text=case["user_text"],
            user_name=case["user_name"],
            persona_runtime=persona_runtime,
            history=case["history"],
        )

        print("OUTPUT:")
        print(result.model_dump(mode="json"))
        print("-" * 80)


if __name__ == "__main__":
    main()
