"""FastAPI server with a REST endpoint and WebSocket broadcast."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="TUI WebSocket Example Server")

# ── Connected WebSocket clients ──────────────────────────────────────────────
connected_clients: list[WebSocket] = []


# ── Models ───────────────────────────────────────────────────────────────────
class Message(BaseModel):
    username: str
    text: str


# ── Helpers ──────────────────────────────────────────────────────────────────
async def broadcast(payload: dict) -> None:
    """Send a JSON payload to every connected WebSocket client."""
    disconnected: list[WebSocket] = []
    for ws in connected_clients:
        try:
            await ws.send_json(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        connected_clients.remove(ws)


# ── REST endpoint ────────────────────────────────────────────────────────────
@app.post("/messages")
async def post_message(msg: Message) -> dict:
    """Accept a message via HTTP POST and broadcast it to all WebSocket clients."""
    payload = {
        "username": msg.username,
        "text": msg.text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await broadcast(payload)
    return {"status": "ok", "message": payload}


# ── WebSocket endpoint ───────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    connected_clients.append(ws)
    try:
        # Keep the connection alive; the server only pushes data.
        while True:
            await asyncio.sleep(1)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)


# ── Entrypoint ───────────────────────────────────────────────────────────────
def main() -> None:
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
