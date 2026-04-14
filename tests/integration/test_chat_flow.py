from apps.core.bootstrap import build_runtime


def test_chat_flow_runs() -> None:
    runtime = build_runtime()
    output = runtime.handle_chat_full(
        text="如果观众说明天考试很紧张，我应该怎么安慰他？",
        user_id="u001",
        username="测试用户",
    )

    assert output.packet.reply_text
    assert output.packet.audio_path is not None
    assert output.packet.subtitle_path is not None
    assert output.packet.live2d_command_path is not None
