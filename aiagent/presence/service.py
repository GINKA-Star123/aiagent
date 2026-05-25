from __future__ import annotations

from datetime import datetime,timezone

from aiagent.presence.live2d_mapper import build_live2d_presence
from aiagent.presence.models import (
    OpeningPayload,
    PresencePayload,
    SessionOpenRequest,
    SessionOpenResponse,
)
from aiagent.presence.opening_generator import (
    choose_opening_kind,
    generate_opening_text,
    update_snapshot_after_open,
)
from aiagent.presence.rhythm import mood_label,choose_presence_state, update_mood_for_time
from aiagent.presence.store import PresenceStore

class PresenceService:
    def __init__(self, store: PresenceStore|None =None) -> None:
        self.store = store or PresenceStore()

    async def open_session(self,req:SessionOpenRequest) -> SessionOpenResponse:
        now = req.client_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo = timezone.utc)

        snapshot = await self.store.get_snapshot(
            user_id = req.user_id,
            username = req.username
        )

        snapshot.mood = update_mood_for_time(now,snapshot.mood)
        state = choose_presence_state(now,snapshot.mood)
        kind = choose_opening_kind(now,snapshot)

        opening_text = generate_opening_text(
            kind=kind,
            now=now,
            snapshot=snapshot,
        )

        live2d = build_live2d_presence(
            state=state,
            kind=kind,
            mood=snapshot.mood,
        )

        updated_snapshot = update_snapshot_after_open(
            snapshot=snapshot,
            now=now,
            recent_topic=req.recent_topic,
        )

        updated_snapshot.mood = snapshot.mood

        await self.store.save_snapshot(updated_snapshot)

        return SessionOpenResponse(
            opening=OpeningPayload(
                kind=kind,
                text=opening_text,
                should_speak=True,
            ),
            presence=PresencePayload(
                state=state,
                mood=mood_label(snapshot.mood),
                energy=round(snapshot.mood.energy, 3),
                fatigue=round(snapshot.mood.fatigue, 3),
                curiosity=round(snapshot.mood.curiosity, 3),
            ),
            live2d=live2d,
            memory={
                "open_count": updated_snapshot.open_count,
                "last_topic": updated_snapshot.last_topic,
                "has_unfinished_hint": bool(updated_snapshot.unfinished_hint),
            },
        )