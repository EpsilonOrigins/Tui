"""Dash – server, TUI, and CLI in one entry point.

Usage:
  dash                            Server + TUI together (default)
  dash --serve                    Headless server only
  dash --client                   Detached TUI client
  dash launch|init|start|stop     Fire action against a running server
"""

from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

# ── Connected WebSocket clients ──────────────────────────────────────────────
connected_clients: list = []
clients_lock = threading.Lock()


# ── State ────────────────────────────────────────────────────────────────────
VALID_ACTIONS = ("launch", "init", "start", "stop")

app_state: dict = {
    "status": "idle",
    "action_log": [],
}


# ── Helpers ──────────────────────────────────────────────────────────────────
def broadcast(payload: dict) -> None:
    """Send a JSON payload to every connected WebSocket client."""
    message = json.dumps(payload)
    disconnected: list = []
    with clients_lock:
        for ws in connected_clients:
            try:
                ws.send(message)
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
def post_message():
    """Accept a message via HTTP POST and broadcast it to all WebSocket clients."""
    data = request.get_json()
    if not data or "username" not in data or "text" not in data:
        return jsonify({"detail": "username and text are required"}), 400
    payload = {
        "type": "message",
        "username": data["username"],
        "text": data["text"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    broadcast(payload)
    return jsonify({"status": "ok", "message": payload})


@app.post("/actions/<action>")
def post_action(action: str):
    """Execute an action (launch, init, start, stop) and broadcast the state change."""
    if action not in VALID_ACTIONS:
        return jsonify({"detail": f"Unknown action: {action}. Valid: {VALID_ACTIONS}"}), 400
    payload = _execute_action(action)
    broadcast(payload)
    return jsonify({"status": "ok", **payload})


@app.get("/status")
def get_status():
    """Return current app state."""
    return jsonify({"status": app_state["status"], "action_log": app_state["action_log"]})


# ── WebSocket endpoint ───────────────────────────────────────────────────────
@sock.route("/ws")
def websocket_endpoint(ws) -> None:
    with clients_lock:
        connected_clients.append(ws)
    try:
        # Keep the connection alive; the server only pushes data.
        while True:
            ws.receive()
    except Exception:
        pass
    finally:
        with clients_lock:
            if ws in connected_clients:
                connected_clients.remove(ws)


# ── Entrypoint ───────────────────────────────────────────────────────────────
def _run_server_in_thread():
    """Start Flask in a daemon thread and return the server instance."""
    from werkzeug.serving import make_server

    server = make_server("0.0.0.0", 8000, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
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
        app.run(host="0.0.0.0", port=8000)
    elif args.client:
        from client import DashApp

        DashApp().run()
    else:
        from client import DashApp

        server = _run_server_in_thread()
        DashApp().run()
        server.shutdown()


if __name__ == "__main__":
    main()
