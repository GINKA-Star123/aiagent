from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.audio import router as audio_router
from apps.api.routes.chat import router as chat_router
from apps.api.routes.control import router as control_router
from apps.api.routes.health import router as health_router
from apps.api.routes.knowledge import router as knowledge_router
from apps.api.routes.memory import router as memory_router
from apps.api.routes.vision import router as vision_router
from apps.api.routes.voice import router as voice_router
from apps.api.routes.multimodal_chat import router as multimodal_chat_router
from apps.api.routes.live2d import router as live2d_router
from apps.api.routes.diagnostics import router as diagnostics_router
from config.settings import settings

logger = logging.getLogger("aiagent.api")

app = FastAPI(title="aiagent api", version="1.0.0")

cors_origins = [
    item.strip()
    for item in settings.api_cors_origins.split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(diagnostics_router)
app.include_router(chat_router)
app.include_router(multimodal_chat_router)
app.include_router(control_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(vision_router)
app.include_router(voice_router)
app.include_router(audio_router)
app.include_router(live2d_router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("API server started.")


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "aiagent api",
        "version": "1.0.0",
    }
