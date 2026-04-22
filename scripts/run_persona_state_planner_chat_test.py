from __future__ import annotations

from aiagent.cognition.planner_normalizer import PlannerNormalizer
from aiagent.cognition.planner_reply import ReplyPlanner
from aiagent.cognition.state_analyzer import StateAnalyzer
from aiagent.cognition.state_normalizer import StateNormalizer
from aiagent.graphs.planner_graph import PlannerRunner
from aiagent.graphs.state_graph import StateRunner
from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.services.llm_service import LLMService
from aiagent.services.planner_llm_service import PlannerLLMService
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


def build_planner_runner() -> PlannerRunner:
    planner_llm_service = PlannerLLMService(settings=settings)
    planner_reply = ReplyPlanner(llm_service=planner_llm_service)
    planner_normalizer = PlannerNormalizer()

    return PlannerRunner(
        planner_reply=planner_reply,
        planner_normalizer=planner_normalizer,
    )


def build_final_system_prompt(
    persona: PersonaRuntime,
    state_result,
    planner_result,
) -> str:
    
    return (
        f"{persona.build_system_prompt()}\n\n"
        f"状态分析结果:\n"
        f"- emotion: {state_result.emotion}\n"
        f"- intent: {state_result.intent}\n"
        f"- topic: {state_result.topic}\n"
        f"- motion_hint: {state_result.motion_hint}\n"
        f"- confidence: {state_result.confidence}\n"
        f"- reasoning: {state_result.reasoning}\n"
        f"- context_summary: {state_result.context_summary}\n\n"
        f"回复规划结果:\n"
        f"- strategy: {planner_result.strategy}\n"
        f"- should_store_memory: {planner_result.should_store_memory}\n"
        f"- should_speak: {planner_result.should_speak}\n"
        f"- target_emotion: {planner_result.target_emotion}\n"
        f"- target_motion: {planner_result.target_motion}\n"
        f"- target_expression: {planner_result.target_expression}\n"
        f"- planner_confidence: {planner_result.confidence}\n"
        f"- planner_reasoning: {planner_result.reasoning}\n"
        f"- reply_instruction: {planner_result.reply_instruction}\n\n"
        "请基于以上 persona、state 和 planner 结果，直接输出最终回复。\n"
        "要求：\n"
        "1. 只输出最终回复，不要解释分析过程。\n"
        "2. 不要自我介绍。\n"
        "3. 不要输出 JSON。\n"
        "4. 回复必须符合角色口吻。\n"
        "5. 优先服从 reply_instruction。\n"
    )


def main() -> None:
    persona = build_persona_runtime()
    state_runner = build_state_runner()
    planner_runner = build_planner_runner()
    llm_service = LLMService(settings=settings)

    test_cases = [
        
        {
            "user_name": "小花",
            "user_text": "阿绫，我们的相遇是否也是永别呢",
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

        planner_result = planner_runner.run(
            user_text=case["user_text"],
            user_name=case["user_name"],
            state_result=state_result,
            persona_runtime=persona,
        )

        system_prompt = build_final_system_prompt(
            persona=persona,
            state_result=state_result,
            planner_result=planner_result,
        )

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

        print("PLANNER RESULT:")
        print(planner_result.model_dump(mode="json"))
        print()

        print("RAW REPLY:")
        print(raw_reply)
        print()

        print("FINAL REPLY:")
        print(final_reply)
        print()

        print("ISSUES:")
        print(issues)
        print("=" * 100)
        print()


if __name__ == "__main__":
    main()
