from apps.core.bootstrap import build_runtime
from config.settings import settings


def main() -> None:
    runtime = build_runtime()

    print("=== RUNTIME CONFIG ===")
    print(
        {
            "llm_provider": settings.llm_provider,
            "tts_provider": settings.tts_provider,
            "asr_provider": settings.asr_provider,
            "rag_embedding_model_name": settings.rag_embedding_model_name,
        }
    )

    print("=== ROUND 1 ===")
    output1 = runtime.handle_chat_full(
        text="如果观众说明天考试很紧张，我应该怎么安慰他？",
        user_id="u001",
        username="阿明",
    )
    print(output1.model_dump())

    print("=== ROUND 2 ===")
    output2 = runtime.handle_chat_full(
        text="那如果他说自己晚上一直睡不着呢？",
        user_id="u001",
        username="阿明",
    )
    print(output2.model_dump())

    print("=== ROUND 3 ===")
    output3 = runtime.handle_chat_full(
        text="说起来我最近也在听轻一点的歌，这样会不会放松一些？",
        user_id="u001",
        username="阿明",
    )
    print(output3.model_dump())

    print("=== CONVERSATION SNAPSHOT ===")
    print(runtime.conversation_state.snapshot())


if __name__ == "__main__":
    main()
