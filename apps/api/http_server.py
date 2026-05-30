from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from cloud.config import cloud_settings
from cloud.middleware import cloud_guard_middleware
from apps.api.middleware import request_logging_middleware
from apps.api.routes.audio import router as audio_router
from apps.api.routes.chat import router as chat_router
from apps.api.routes.cloud import router as cloud_router
from apps.api.routes.cloud_gpu import router as cloud_gpu_router
from apps.api.routes.cloud_ops import router as cloud_ops_router
from apps.api.routes.cloud_tasks import router as cloud_tasks_router
from apps.api.routes.control import router as control_router
from apps.api.routes.diagnostics import router as diagnostics_router
from apps.api.routes.health import router as health_router
from apps.api.routes.knowledge import router as knowledge_router
from apps.api.routes.live2d import router as live2d_router
from apps.api.routes.memory import router as memory_router
from apps.api.routes.multimodal_chat import router as multimodal_chat_router
from apps.api.routes.vision import router as vision_router
from apps.api.routes.voice import router as voice_router
from apps.api.routes.voice_realtime import router as voice_realtime_router
from apps.api.routes.session import router as session_router
from apps.api.routes.dashboard import router as dashboard_router
from config.settings import settings

logger = logging.getLogger("aiagent.api")

app = FastAPI(title="aiagent api", version="1.0.0")

app.middleware("http")(cloud_guard_middleware)
app.middleware("http")(request_logging_middleware)

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

if cloud_settings.storage_provider.lower() == "local":
    storage_root = Path(cloud_settings.local_storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/cloud-files",
        StaticFiles(directory=str(storage_root)),
        name="cloud-files",
    )

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(cloud_router)
app.include_router(cloud_tasks_router)
app.include_router(cloud_gpu_router)
app.include_router(cloud_ops_router)
app.include_router(diagnostics_router)
app.include_router(chat_router)
app.include_router(multimodal_chat_router)
app.include_router(control_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(vision_router)
app.include_router(voice_router)
app.include_router(voice_realtime_router)
app.include_router(audio_router)
app.include_router(live2d_router)
app.include_router(session_router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "API server started cloud_mode=%s storage_provider=%s",
        cloud_settings.cloud_mode,
        cloud_settings.storage_provider,
    )


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "aiagent api",
        "version": "1.0.0",
        "cloud_mode": cloud_settings.cloud_mode,
    }