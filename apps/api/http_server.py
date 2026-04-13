"""HTTP API server placeholder."""

from fastapi import FastAPI,WebSocket

from apps.api.routes.chat import router as chat_router
from apps.api.routes.health import router as health_router
from apps.api.ws_server import chat_websocket_endpoint

app = FastAPI(title="AI Agent API Server")

app.include_router(health_router)
app.include_router(chat_router)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await chat_websocket_endpoint(websocket)