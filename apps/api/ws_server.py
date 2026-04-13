"""WebSocket API server placeholder."""

from fastapi import WebSocket, WebSocketDisconnect
from apps.core.bootstrap import build_runtime

runtime = build_runtime()

async def chat_websocket_endpoint(websocket: WebSocket) ->None:
    await websocket.accept()
    try :
        while True:
            data = await websocket.receive_json()

            user_id = data.get("user_id","guest")
            username =data.get("username","Guest")
            text = data.get("text","")

            reply = runtime.handle_chat(
                text = text,
                user_id = user_id,
                username = username,
            )

            await websocket.send_json(
                {
                    "type":"reply",
                    "user_id": user_id,
                    "username": username,
                    "reply": reply,
                }
            )
    except WebSocketDisconnect:
        print("WebSocket disconnected")