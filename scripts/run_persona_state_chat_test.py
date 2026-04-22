from __future__ import annotations

from aiagent.cognition.state_analyzer import StateAnalyzer
from aiagent.cognition.state_normalizer import StateNormalizer
from aiagent.graphs.state_graph import StateRunner
from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.services.llm_service import LLMService
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


def build_final_system_prompt(persona: PersonaRuntime, state_result) -> str:
    return (
        f"{persona.build_system_prompt()}\n\n"
        f"当前状态分析结果:\n"
        f"- emotion: {state_result.emotion}\n"
        f"- intent: {state_result.intent}\n"
        f"- topic: {state_result.topic}\n"
        f"- motion_hint: {state_result.motion_hint}\n"
        f"- confidence: {state_result.confidence}\n"
        f"- reasoning: {state_result.reasoning}\n\n"
        f"上下文摘要:\n{state_result.context_summary}\n\n"
        "请基于以上 persona 和 state 分析，直接输出最终回复。\n"
        "要求：\n"
        "1. 不要解释分析过程。\n"
        "2. 不要自我介绍。\n"
        "3. 不要输出 JSON。\n"
        "4. 回复要像角色本人在实时聊天。\n"
    )


def main() -> None:
    persona = build_persona_runtime()
    state_runner = build_state_runner()
    llm_service = LLMService(settings=settings)

    test_cases = [
        {
            "user_name": "小花",
            "user_text": "阿绫你是真实存在的吗",
            "history": ["小花刚看完绫形diamond演唱会"],
        },
        {
            "user_name": "小花",
            "user_text": "阿绫你喜欢天依吗",
            "history": [],
        },
    ]

    print("=== PERSONA SUMMARY ===")
    print(persona.summary())
    print()

    for index, case in enumerate(test_cases, start=1):
        print(f"========== TEST {index} ==========")
        print("INPUT:")
        print(case)
        print()

        state_result = state_runner.run(
            user_text=case["user_text"],
            user_name=case["user_name"],
            persona_runtime=persona,
            history=case["history"],
        )

        system_prompt = build_final_system_prompt(persona, state_result)

        messages = llm_service.build_messages(
            system_prompt=system_prompt,
            user_text=case["user_text"],
        )

        raw_reply = llm_service.invoke_messages(
            messages=messages,
            fallback_text=case["user_text"],
            mode="chat",
            persona_name=persona.alias or persona.name,
        )

        final_reply = persona.normalize_reply(raw_reply)
        issues = persona.validate_reply(final_reply)

        print("STATE RESULT:")
        print(state_result.model_dump(mode="json"))
        print()

        print("RAW REPLY:")
        print(raw_reply)
        print()

        print("FINAL REPLY:")
        print(final_reply)
        print()

        print("ISSUES:")
        print(issues)
        print("=" * 80)
        print()


if __name__ == "__main__":
    main()
