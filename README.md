# TUI WebSocket Example

A minimal example app with a **Textual** TUI client that sends messages to a **FastAPI** server via HTTP POST and receives real-time updates over a WebSocket.

## Architecture

```
┌──────────────┐  POST /messages   ┌──────────────┐
│  Textual TUI │ ────────────────► │ FastAPI      │
│  (client.py) │                   │ (server.py)  │
│              │ ◄──────────────── │              │
└──────────────┘   WS /ws          └──────────────┘
```

- **`server.py`** – FastAPI app with a `POST /messages` endpoint and a `/ws` WebSocket that broadcasts every new message to all connected clients.
- **`client.py`** – Textual TUI that connects to the WebSocket on startup and sends messages via HTTP POST. Incoming broadcasts appear in the chat log in real time.

## Setup

```bash
pip install -e .
```

## Running

**Default — server + TUI together:**

```bash
python server.py
```

This starts the FastAPI server in the background and opens the TUI. When you quit the TUI (Ctrl+Q), the server shuts down with it.

**Headless server only:**

```bash
python server.py --serve
```

Runs just the server on `http://localhost:8000` (with hot-reload). Connect additional TUI clients from other terminals with `python client.py`.

## Usage

- Type a username in the left input field (defaults to `user1`).
- Type a message in the right input field and press **Enter** to send.
- All connected clients see the message appear in the chat log via WebSocket.
- Press **Ctrl+Q** to quit the TUI.
