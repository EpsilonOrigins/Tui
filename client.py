"""Textual TUI client that POSTs messages to the FastAPI server and receives
WebSocket updates in real time."""

from __future__ import annotations

import asyncio
import json

import httpx
import websockets
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


class ChatApp(App):
    """A simple chat TUI that talks to a FastAPI backend."""

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
    ]

    def compose(self) -> ComposeResult:
        yield Header(name="TUI Chat")
        yield Vertical(
            RichLog(id="chat-log", highlight=True, markup=True),
            Static("Connecting...", id="status"),
            Horizontal(
                Input(placeholder="Username", id="username", value="user1"),
                Input(placeholder="Type a message...", id="message"),
                id="input-area",
            ),
        )
        yield Footer()

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
                            ts = data.get("timestamp", "")
                            user = data.get("username", "?")
                            text = data.get("text", "")
                            log.write(f"[bold]{user}[/bold] ({ts}): {text}")
                    except websockets.ConnectionClosed:
                        status.update("Disconnected – reconnecting...")
            except Exception:
                status.update("Cannot reach server – retrying...")
                await asyncio.sleep(2)

    # ── Send message on Enter ────────────────────────────────────────────────
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "message":
            return

        text = event.value.strip()
        if not text:
            return

        username = self.query_one("#username", Input).value.strip() or "anon"
        event.input.value = ""

        status = self.query_one("#status", Static)

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
    ChatApp().run()


if __name__ == "__main__":
    main()
