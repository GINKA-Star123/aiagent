from apps.core.bootstrap import build_runtime
from config.settings import settings


def main() -> None:
    runtime = build_runtime()

    print("=== RUNTIME CONFIG ===")
    print(
        {
            "llm_provider": settings.llm_provider,
            "enable_mock_llm": settings.enable_mock_llm,
            "llm_model": settings.llm_model,
        }
    )

    print("=== REAL LLM TEST 1 ===")
    output1 = runtime.handle_chat_full(
        text="如果观众说明天考试很紧张，我应该怎么安慰他？",
        user_id="u001",
        username="阿明",
    )
    print(output1.model_dump())

    print("=== REAL LLM TEST 2 ===")
    output2 = runtime.handle_chat_full(
        text="观众说自己喜欢音乐，我可以怎么接话？",
        user_id="u002",
        username="小雨",
    )
    print(output2.model_dump())

    print("=== SPEAKING STATE ===")
    print(runtime.get_speaking_state().model_dump())


if __name__ == "__main__":
    main()
