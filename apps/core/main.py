"""Application entrypoint for the core streamer runtime."""

from apps.core.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()

    print("=== CHAT TEST 1 ===")
    output1 = runtime.handle_chat_full(
        text="你好，我叫阿明，我喜欢东方project。",
        user_id="u001",
        username="阿明",
    )
    print(output1.model_dump())

    print("=== CHAT TEST 2 ===")
    output2 = runtime.handle_chat_full(
        text="你还记得我刚刚说了什么吗？",
        user_id="u001",
        username="阿明",
    )
    print(output2.model_dump())

    print("=== ASR TEST ===")
    output3 = runtime.handle_asr_text(
        audio_text="我今天有点紧张，明天考试。",
        user_id="u002",
        username="语音观众",
    )
    print(output3.model_dump())

    print("=== SPEAKING STATE ===")
    print(runtime.get_speaking_state().model_dump())


if __name__ == "__main__":
    main()
