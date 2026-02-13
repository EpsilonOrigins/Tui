# Dash

Server, TUI, and CLI in one entry point. Built with **FastAPI** + **Textual**.

## Architecture

```
┌──────────────┐  POST /messages       ┌──────────────┐
│  Dash TUI    │  POST /actions/{act}  │  Dash Server │
│  (client.py) │ ────────────────────► │  (dash.py)   │
│              │ ◄──────────────────── │              │
└──────────────┘   WS /ws              └──────────────┘
```

- **`dash.py`** – FastAPI server, CLI dispatcher, and TUI launcher.
- **`client.py`** – Textual TUI that connects over WebSocket and sends via HTTP POST.

## Setup

```bash
pip install -e .
```

## Running

```bash
dash                # Server + TUI together (default)
dash --serve        # Headless server only
dash --client       # Detached TUI client (connects to running server)
dash launch         # Fire action against a running server
dash init
dash start
dash stop
```

Or run directly:

```bash
python dash.py
python dash.py --serve
python dash.py start
```

## Usage

- Type a username in the left input field (defaults to `user1`).
- Type a message in the right input field and press **Enter** to send.
- Type `/launch`, `/init`, `/start`, or `/stop` to trigger actions from the TUI.
- All connected clients see messages and state changes via WebSocket.
- Press **Ctrl+Q** to quit the TUI.
