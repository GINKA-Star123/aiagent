"""Dialogue flow management."""

from collections import defaultdict
from datetime import datetime

from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import OutputEvent


class DialogueManager:
    def __init__(self):
        self.global_paused: bool = False
        self.user_paused: set[str] = set()
        self.turn_counts: dict[str, int] = defaultdict(int)
        self.last_reply_text: dict[str, str] = {}
        self.last_input_reply: dict[str, str] = {}
        self.last_active_at: dict[str, str] = {}

    def should_accept(self, event: InputEvent) -> tuple[bool, str]:
        if self.global_paused:
            return False, "global paused"
        if event.user_id in self.user_paused:
            return False, f"user {event.user_id} paused"

        if not event.text.strip():
            return False, "empty text"

        return True, ""

    def record_turn(self, session_id: str, event: InputEvent, output: OutputEvent) -> None:
        self.turn_counts[session_id] += 1
        self.last_input_reply[session_id] = event.text
        self.last_reply_text[session_id] = output.packet.reply_text
        self.last_active_at[session_id] = datetime.now().isoformat(timespec="seconds")

    def pause_global(self) -> None:
        self.global_paused = True

    def resume_global(self) -> None:
        self.global_paused = False

    def pause_user(self, user_id: str) -> None:
        self.user_paused.add(user_id)

    def resume_user(self, user_id: str) -> None:
        self.user_paused.discard(user_id)

    def reset_session(self, session_id: str) -> None:
        self.turn_counts.pop(session_id, None)
        self.last_input_reply.pop(session_id, None)
        self.last_reply_text.pop(session_id, None)
        self.last_active_at.pop(session_id, None)

    def snapshot(self) -> dict:
        return {
            "global_paused": self.global_paused,
            "paused_users": sorted(self.user_paused),
            "turn_counts": dict(self.turn_counts),
            "last_input_text": dict(self.last_input_reply),
            "last_reply_text": dict(self.last_reply_text),
            "last_active_at": dict(self.last_active_at),
        }
