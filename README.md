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

**1. Start the server** (in one terminal):

```bash
python server.py
```

The server listens on `http://localhost:8000`.

**2. Start the TUI client** (in another terminal):

```bash
python client.py
```

Open multiple TUI instances to see messages broadcast across all clients.

## Usage

- Type a username in the left input field (defaults to `user1`).
- Type a message in the right input field and press **Enter** to send.
- All connected clients see the message appear in the chat log via WebSocket.
- Press **Ctrl+Q** to quit the TUI.
