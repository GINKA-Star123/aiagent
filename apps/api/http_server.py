from __future__ import annotations

import logging

from fastapi import FastAPI

from apps.api.routes.audio import router as audio_router
from apps.api.routes.chat import router as chat_router
from apps.api.routes.control import router as control_router
from apps.api.routes.health import router as health_router
from apps.api.routes.knowledge import router as knowledge_router
from apps.api.routes.memory import router as memory_router
from apps.api.routes.voice import router as voice_router

logger = logging.getLogger("aiagent.api")

app = FastAPI(title="aiagent api")

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(control_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(voice_router)
app.include_router(audio_router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("API server started.")
