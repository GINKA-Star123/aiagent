from __future__ import annotations

from aiagent.schemas.inputs import InputEvent, InputSource
from aiagent.schemas.outputs import OutputEvent, ResponsePacket
from aiagent.state.conversation_state import ConversationState


def _event(
    text: str,
    session_id: str,
    turn_id: str,
    user_name: str = "U",
) -> InputEvent:
    return InputEvent(
        source=InputSource.CHAT,
        user_id="u1",
        user_name=user_name,
        text=text,
        session_id=session_id,
        turn_id=turn_id,
    )


def _reply(reply_text: str, session_id: str, turn_id: str) -> OutputEvent:
    return OutputEvent(
        packet=ResponsePacket(
            reply_text=reply_text,
            metadata={"session_id": session_id, "turn_id": turn_id},
        )
    )


def test_history_only_contains_target_session():
    state = ConversationState()
    state.add_input(_event("A1", "s-a", "s-a:1"))
    state.add_input(_event("B1", "s-b", "s-b:1"))
    state.add_input(_event("A2", "s-a", "s-a:2"))
    state.add_output(_reply("a1", "s-a", "s-a:1"))
    state.add_output(_reply("b1", "s-b", "s-b:1"))

    pairs_a = state.recent_dialogue_pairs(session_id="s-a")
    pairs_b = state.recent_dialogue_pairs(session_id="s-b")

    assert [pair["input"] for pair in pairs_a] == ["A1"]
    assert [pair["reply"] for pair in pairs_a] == ["a1"]
    assert [pair["input"] for pair in pairs_b] == ["B1"]
    assert [pair["reply"] for pair in pairs_b] == ["b1"]


def test_history_without_session_id_keeps_all_turns():
    state = ConversationState()
    state.add_input(_event("A1", "s-a", "s-a:1"))
    state.add_input(_event("B1", "s-b", "s-b:1"))
    state.add_output(_reply("a1", "s-a", "s-a:1"))
    state.add_output(_reply("b1", "s-b", "s-b:1"))

    pairs = state.recent_dialogue_pairs()

    assert [pair["input"] for pair in pairs] == ["A1", "B1"]
    assert [pair["reply"] for pair in pairs] == ["a1", "b1"]


def test_history_skips_turn_without_reply():
    state = ConversationState()
    state.add_input(_event("A1", "s-a", "s-a:1"))
    state.add_output(_reply("a1", "s-a", "s-a:1"))
    state.add_input(_event("A2", "s-a", "s-a:2"))  # 当前轮：还没有回复

    pairs = state.recent_dialogue_pairs(session_id="s-a")

    assert pairs == [{"user": "U", "input": "A1", "reply": "a1"}]


def test_history_falls_back_to_order_without_turn_id():
    state = ConversationState()
    state.add_input(InputEvent(source=InputSource.CHAT, user_id="u1", text="X1"))
    state.add_output(
        OutputEvent(packet=ResponsePacket(reply_text="x1", metadata={}))
    )

    pairs = state.recent_dialogue_pairs()

    assert pairs == [{"user": "guest", "input": "X1", "reply": "x1"}]