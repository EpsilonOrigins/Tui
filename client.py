"""Dash TUI client – sends messages and commands to the Dash server,
receives real-time WebSocket updates.

Commands (type in the message input):
  /launch  /init  /start  /stop
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import websockets
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

_base = os.environ.get("DASH_SERVER_URL", "http://localhost:8000").rstrip("/")
SERVER_URL = _base
WS_URL = _base.replace("http://", "ws://", 1).replace("https://", "wss://", 1) + "/ws"
COMMANDS = {"/launch", "/init", "/start", "/stop"}


class DashApp(App):
    """Dash TUI client."""

    CSS = """
    #chat-log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    #input-area {
        height: auto;
        dock: bottom;
        padding: 1 0;
    }
    #username {
        width: 20;
    }
    #message {
        width: 1fr;
    }
    #status {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "focus_input", "Focus input"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(name="Dash")
        yield Vertical(
            RichLog(id="chat-log", highlight=True, markup=True),
            Static("Connecting...", id="status"),
            Horizontal(
                Input(placeholder="Username", id="username", value="user1"),
                Input(
                    placeholder="Message or /launch /init /start /stop",
                    id="message",
                ),
                id="input-area",
            ),
        )
        yield Footer()

    def action_focus_input(self) -> None:
        self.query_one("#message", Input).focus()

    def on_mount(self) -> None:
        self.listen_ws()

    # ── WebSocket listener (background worker) ──────────────────────────────
    @work(exclusive=True)
    async def listen_ws(self) -> None:
        status = self.query_one("#status", Static)
        log = self.query_one("#chat-log", RichLog)

        while True:
            try:
                status.update("Connected to server")
                async for ws in websockets.connect(WS_URL):
                    try:
                        async for raw in ws:
                            data = json.loads(raw)
                            if data.get("type") == "action":
                                action = data.get("action", "?")
                                prev = data.get("previous_status", "?")
                                new = data.get("status", "?")
                                ts = data.get("timestamp", "")
                                log.write(
                                    f"[bold yellow]>> {action}[/bold yellow] "
                                    f"[dim]{prev} -> {new}[/dim] ({ts})"
                                )
                            else:
                                ts = data.get("timestamp", "")
                                user = data.get("username", "?")
                                text = data.get("text", "")
                                log.write(f"[bold]{user}[/bold] ({ts}): {text}")
                    except websockets.ConnectionClosed:
                        status.update("Disconnected – reconnecting...")
            except Exception:
                status.update("Cannot reach server – retrying...")
                await asyncio.sleep(2)

    # ── Send message or command on Enter ─────────────────────────────────────
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "message":
            return

        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        status = self.query_one("#status", Static)

        # Route /commands to the action endpoint
        if text in COMMANDS:
            action = text.lstrip("/")
            await self._send_action(action, status)
        else:
            username = self.query_one("#username", Input).value.strip() or "anon"
            await self._send_message(username, text, status)

    async def _send_action(self, action: str, status: Static) -> None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{SERVER_URL}/actions/{action}")
                resp.raise_for_status()
                status.update(f"Action '{action}' executed")
        except httpx.HTTPError as exc:
            status.update(f"Action failed: {exc}")

    async def _send_message(self, username: str, text: str, status: Static) -> None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SERVER_URL}/messages",
                    json={"username": username, "text": text},
                )
                resp.raise_for_status()
                status.update("Message sent")
        except httpx.HTTPError as exc:
            status.update(f"Send failed: {exc}")


def main() -> None:
    DashApp().run()


if __name__ == "__main__":
    main()
