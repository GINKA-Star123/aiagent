"""Application entrypoint for the core streamer runtime."""

from apps.core.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()

    user_text = "你好，今天直播间怎么样？"
    reply = runtime.handle_chat(
        text=user_text,
        user_id="u001",
        username="测试观众",
    )

    print("=== INPUT ===")
    print(user_text)
    print("=== OUTPUT ===")
    print(reply)


if __name__ == "__main__":
    main()
