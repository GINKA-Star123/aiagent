from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.staticfiles import StaticFiles

from aiagent.perception.voice_call_store import (
    VoiceCallStoreConflictError,
    VoiceCallStoreUnavailableError,
)

from apps.api.response_utils import error_message_response
from apps.api.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
)
from cloud.config import cloud_settings
from cloud.middleware import cloud_guard_middleware
from apps.api.http_security import build_cors_policy
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

app.add_exception_handler(HTTPException, http_exception_handler) #type: ignore
app.add_exception_handler(RequestValidationError, validation_exception_handler) #type: ignore
app.middleware("http")(cloud_guard_middleware)
app.middleware("http")(request_logging_middleware)

cors_policy = build_cors_policy(
    settings.api_cors_origins,
    app_env=settings.app_env,
    cloud_mode=cloud_settings.cloud_mode,
    allow_credentials=settings.api_cors_allow_credentials,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cors_policy.origins),
    allow_credentials=cors_policy.allow_credentials,
    allow_methods=list(cors_policy.allow_methods),
    allow_headers=list(cors_policy.allow_headers),
    expose_headers=list(cors_policy.expose_headers),
    max_age=600,
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
        (
            "API server started "
            "cloud_mode=%s "
            "storage_provider=%s "
            "cors_origin_count=%s"
        ),
        cloud_settings.cloud_mode,
        cloud_settings.storage_provider,
        len(cors_policy.origins),
    )


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "aiagent api",
        "version": "1.0.0",
        "cloud_mode": cloud_settings.cloud_mode,
    }

async def voice_call_store_unavailable_handler(
    request: Request,
    exc: VoiceCallStoreUnavailableError,
) -> Response:
    return error_message_response(
        stage=exc.stage,
        error=str(exc),
        status_code=503,
    )


async def voice_call_store_conflict_handler(
    request: Request,
    exc: VoiceCallStoreConflictError,
) -> Response:
    return error_message_response(
        stage=exc.stage,
        error=str(exc),
        status_code=409,
    )


app.add_exception_handler(
    VoiceCallStoreUnavailableError,
    voice_call_store_unavailable_handler, # type:ignore
)
app.add_exception_handler(
    VoiceCallStoreConflictError,
    voice_call_store_conflict_handler, #type:ignore
)