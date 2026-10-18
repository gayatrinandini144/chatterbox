"""
app.py
Real-time chat server: Flask + Flask-SocketIO.
No accounts — users join with a nickname. Supports group chat rooms
and 1-to-1 direct messages, plus a live online-users list.
"""

import os

from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit

import database as db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

db.init_db()

# sid -> nickname
online_users = {}
# nickname (lowercase) -> sid, the inverse lookup used to route DMs directly
sid_by_nickname = {}
# sid -> current channel (room name or dm channel) the client is actively viewing
active_channel = {}


def broadcast_user_list():
    emit("user_list", sorted(set(online_users.values())), broadcast=True)


def broadcast_room_list():
    emit("room_list", db.list_rooms(), broadcast=True)


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    # Nickname is set explicitly by the client after connecting.
    pass


@socketio.on("disconnect")
def handle_disconnect():
    nickname = online_users.pop(request.sid, None)
    active_channel.pop(request.sid, None)
    if nickname:
        sid_by_nickname.pop(nickname.lower(), None)
        broadcast_user_list()


@socketio.on("set_nickname")
def handle_set_nickname(data):
    nickname = (data.get("nickname") or "").strip()[:24]
    if not nickname:
        emit("nickname_error", {"error": "Nickname can't be empty."})
        return
    if nickname.lower() in {n.lower() for sid, n in online_users.items() if sid != request.sid}:
        emit("nickname_error", {"error": "That nickname is already taken. Try another."})
        return

    online_users[request.sid] = nickname
    sid_by_nickname[nickname.lower()] = request.sid
    emit("nickname_ok", {"nickname": nickname})
    broadcast_user_list()
    broadcast_room_list()

    # Drop them into the default room automatically.
    _join_channel(request.sid, "general", is_room=True)


def _join_channel(sid, channel, is_room):
    previous = active_channel.get(sid)
    if previous and previous != channel:
        leave_room(previous, sid=sid)

    join_room(channel, sid=sid)
    active_channel[sid] = channel

    history = db.get_history(channel)
    event_name = "room_history" if is_room else "dm_history"
    payload = {"channel": channel, "messages": history}
    if not is_room:
        payload["with"] = channel.split(":")[2] if channel.split(":")[1] == online_users.get(sid, "").lower() else channel.split(":")[1]
    socketio.emit(event_name, payload, room=sid)


@socketio.on("join_room_event")
def handle_join_room(data):
    room_name = (data.get("room") or "").strip()[:32]
    if not room_name:
        return
    db.create_room_if_missing(room_name)
    _join_channel(request.sid, room_name, is_room=True)
    broadcast_room_list()


@socketio.on("start_dm")
def handle_start_dm(data):
    target = (data.get("nickname") or "").strip()
    me = online_users.get(request.sid)
    if not me or not target or target == me:
        return
    channel = db.dm_channel_name(me, target)
    _join_channel(request.sid, channel, is_room=False)


@socketio.on("send_message")
def handle_send_message(data):
    sender = online_users.get(request.sid)
    channel = active_channel.get(request.sid)
    text = (data.get("text") or "").strip()
    if not sender or not channel or not text:
        return
    text = text[:1000]
    message = db.save_message(channel, sender, text)

    is_room = not channel.startswith("dm:")

    if is_room:
        emit("new_message", message, room=channel)
        return

    # DMs are routed directly by nickname rather than relying on the
    # recipient having that thread open (i.e. having joined the room),
    # so the message still arrives even if they're looking elsewhere.
    _, nick_a, nick_b = channel.split(":")
    for nick in (nick_a, nick_b):
        target_sid = sid_by_nickname.get(nick)
        if target_sid:
            socketio.emit("new_dm", message, room=target_sid)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
