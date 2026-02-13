"""Dash – server, TUI, and CLI in one entry point.

Usage:
  dash                            Server + TUI together (default)
  dash --serve                    Headless server only
  dash --client                   Detached TUI client
  dash launch|init|start|stop     Fire action against a running server
"""

from __future__ import annotations

import argparse
import asyncio
import threading
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Dash")

# ── Connected WebSocket clients ──────────────────────────────────────────────
connected_clients: list[WebSocket] = []


# ── Models ───────────────────────────────────────────────────────────────────
class Message(BaseModel):
    username: str
    text: str


# ── State ────────────────────────────────────────────────────────────────────
VALID_ACTIONS = ("launch", "init", "start", "stop")

app_state: dict = {
    "status": "idle",
    "action_log": [],
}


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


def _execute_action(action: str) -> dict:
    """Run an action and return the result payload."""
    now = datetime.now(timezone.utc).isoformat()
    previous = app_state["status"]

    if action == "launch":
        app_state["status"] = "launched"
    elif action == "init":
        app_state["status"] = "initialized"
    elif action == "start":
        app_state["status"] = "running"
    elif action == "stop":
        app_state["status"] = "stopped"

    entry = {"action": action, "previous": previous, "new": app_state["status"], "timestamp": now}
    app_state["action_log"].append(entry)

    return {
        "type": "action",
        "action": action,
        "previous_status": previous,
        "status": app_state["status"],
        "timestamp": now,
    }


# ── REST endpoints ───────────────────────────────────────────────────────────
@app.post("/messages")
async def post_message(msg: Message) -> dict:
    """Accept a message via HTTP POST and broadcast it to all WebSocket clients."""
    payload = {
        "type": "message",
        "username": msg.username,
        "text": msg.text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await broadcast(payload)
    return {"status": "ok", "message": payload}


@app.post("/actions/{action}")
async def post_action(action: str) -> dict:
    """Execute an action (launch, init, start, stop) and broadcast the state change."""
    if action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}. Valid: {VALID_ACTIONS}")
    payload = _execute_action(action)
    await broadcast(payload)
    return {"status": "ok", **payload}


@app.get("/status")
async def get_status() -> dict:
    """Return current app state."""
    return {"status": app_state["status"], "action_log": app_state["action_log"]}


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
def _run_server_in_thread() -> uvicorn.Server:
    """Start uvicorn in a daemon thread and return the Server instance."""
    config = uvicorn.Config("dash:app", host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


def _cli_action(action: str) -> None:
    """POST an action to a running server and print the result."""
    import httpx

    try:
        resp = httpx.post(f"http://localhost:8000/actions/{action}")
        resp.raise_for_status()
        data = resp.json()
        print(f"{action}: {data['previous_status']} -> {data['status']}")
    except httpx.ConnectError:
        print(f"Error: cannot connect to server at localhost:8000")
        raise SystemExit(1)
    except httpx.HTTPStatusError as exc:
        print(f"Error: {exc.response.json().get('detail', exc)}")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="dash", description="Dash – server, TUI, and CLI")
    parser.add_argument(
        "action",
        nargs="?",
        choices=VALID_ACTIONS,
        help="Run an action against a running server and exit",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--serve",
        action="store_true",
        help="Run headless server only (no TUI)",
    )
    mode.add_argument(
        "--client",
        action="store_true",
        help="Run TUI only, connecting to an already-running server",
    )
    args = parser.parse_args()

    if args.action:
        _cli_action(args.action)
    elif args.serve:
        uvicorn.run("dash:app", host="0.0.0.0", port=8000, reload=True)
    elif args.client:
        from client import DashApp

        DashApp().run()
    else:
        from client import DashApp

        server = _run_server_in_thread()
        DashApp().run()
        server.should_exit = True


if __name__ == "__main__":
    main()
