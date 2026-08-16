# Chatterbox — real-time chat app

A Python full-stack real-time chat app: Flask + Flask-SocketIO on the
backend, vanilla JS + WebSockets on the frontend, SQLite for message
history. No accounts — you join with just a nickname.

## Features

- **Nickname join** — no signup, just type a call sign and you're in.
- **Group chat rooms** — join `general` by default, or create/switch to
  any named room from the sidebar. Messages persist per room.
- **Direct messages** — click any online user to open a private 1-to-1
  thread. DMs are delivered instantly even if the recipient hasn't
  opened that thread yet.
- **Live online users list** — updates in real time as people join and
  leave.
- **Message history** — stored in SQLite, reloaded whenever you switch
  into a room or DM.

## Project structure

```
chatapp/
├── app.py                 Flask + Flask-SocketIO server, all socket events
├── database.py             SQLite helper (rooms + messages)
├── requirements.txt
├── templates/
│   └── index.html          Single-page UI
└── static/
    ├── css/style.css
    └── js/main.js           Socket.IO client logic
```

## Setup

1. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python app.py
   ```

4. Open **http://localhost:5000** in a couple of browser tabs (or
   different browsers) to chat between them.

The SQLite database file `chat.db` is created automatically on first
run, in the same folder as `app.py`.

## How it works

- **Joining**: the client emits `set_nickname`; the server rejects it
  if empty or already taken by another connected user, otherwise adds
  you to `general` and broadcasts the updated online-users list.
- **Rooms**: `join_room_event` creates the room if it doesn't exist yet
  and moves your socket into it, sending back the last 100 messages as
  `room_history`.
- **DMs**: `start_dm` computes a deterministic channel name from the
  two nicknames (e.g. `dm:bob:gaya`), regardless of who started it, so
  both sides land on the same thread and history.
- **Sending**: `send_message` saves to SQLite and broadcasts to
  everyone in the room (for group chat) or routes directly to both
  participants by nickname (for DMs, so it arrives even if they're
  looking at a different channel right now).

## Known limitations (by design, given the "no accounts" scope)

- Nicknames aren't reserved between sessions — if you disconnect,
  someone else can take your nickname, and reconnecting under the same
  name just starts a fresh session (your message *history* is still
  there since it's keyed by name, but there's no real identity/auth).
- No typing indicators, read receipts, or file/image sharing — kept
  out of scope per the current spec, but the socket-event structure
  (`static/js/main.js` + `app.py`) makes them straightforward to add
  later if you want them.

## Next steps if you want to extend it

- Add typing indicators (`typing` socket event + a debounced UI hint).
- Add auth (Flask-Login + a `users` table) if you want persistent
  identity instead of session nicknames.
- Deploy with `eventlet` or `gunicorn -k eventlet` behind a reverse
  proxy (Flask's built-in dev server isn't for production).
