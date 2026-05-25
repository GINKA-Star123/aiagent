from __future__ import annotations

import logging

from fastapi import APIRouter
from starlette.responses import JSONResponse

from aiagent.presence.models import SessionOpenRequest
from aiagent.presence.service import PresenceService

router = APIRouter()
logger = logging.getLogger("aiagent.api.session")

presence_service = PresenceService()


@router.post("/session/open")
async def session_open(req: SessionOpenRequest):
    try:
        result = await presence_service.open_session(req)
        return JSONResponse(
            content=result.model_dump(mode="json"),
        )
    except Exception as exc:
        logger.exception("/session/open failed: %s", exc)

        fallback_text = "你来了。我刚刚在待机，现在可以开始。"

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "degraded": True,
                "opening": {
                    "kind": "first_meet",
                    "text": fallback_text,
                    "should_speak": True,
                },
                "presence": {
                    "state": "listening",
                    "mood": "neutral",
                    "energy": 0.5,
                    "fatigue": 0.2,
                    "curiosity": 0.6,
                },
                "live2d": {
                    "expression": "soft_smile",
                    "motion": "wave_small",
                    "suggested_delay_ms": 600,
                    "eye": {
                        "blink": True,
                        "look_at": "user",
                    },
                    "mouth": {
                        "mode": "tts",
                    },
                    "scene": {
                        "background_id": "room_default",
                        "lighting": "normal",
                        "effect": "none",
                    },
                },
                "memory": {
                    "open_count": 0,
                    "last_topic": "",
                    "has_unfinished_hint": False,
                },
                "error": str(exc),
            },
        )