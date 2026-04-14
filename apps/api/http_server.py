"""HTTP API server placeholder."""

import logging

from fastapi import FastAPI, WebSocket

from apps.api.routes.chat import router as chat_router
from apps.api.routes.health import router as health_router
from apps.api.ws_server import chat_websocket_endpoint

logger = logging.getLogger("aiagent.api")

app = FastAPI(title="aiagent api")

app.include_router(health_router)
app.include_router(chat_router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("API server started.")


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await chat_websocket_endpoint(websocket)
