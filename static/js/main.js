// ---------- Theme (dark / light) ----------
const THEME_KEY = "chatterbox-theme";

function getPreferredTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  applyTheme(current === "light" ? "dark" : "light");
}

applyTheme(getPreferredTheme());
document.getElementById("theme-toggle-gate").addEventListener("click", toggleTheme);
document.getElementById("theme-toggle-app").addEventListener("click", toggleTheme);

const socket = io();

let myNickname = null;
let currentChannel = null;   // room name, or "dm:a:b"
let currentIsRoom = true;
let currentDmPartner = null;

// ---------- DOM refs ----------
const gate = document.getElementById("gate");
const app = document.getElementById("app");
const nicknameForm = document.getElementById("nickname-form");
const nicknameInput = document.getElementById("nickname-input");
const nicknameError = document.getElementById("nickname-error");
const myNicknameLabel = document.getElementById("my-nickname");

const roomList = document.getElementById("room-list");
const newRoomForm = document.getElementById("new-room-form");
const newRoomInput = document.getElementById("new-room-input");

const userList = document.getElementById("user-list");
const onlineCount = document.getElementById("online-count");

const channelCode = document.getElementById("channel-code");
const channelTitle = document.getElementById("channel-title");
const messageList = document.getElementById("message-list");
const messageForm = document.getElementById("message-form");
const messageInput = document.getElementById("message-input");

// ---------- Nickname join ----------
nicknameForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const nickname = nicknameInput.value.trim();
  if (!nickname) return;
  socket.emit("set_nickname", { nickname });
});

socket.on("nickname_error", (data) => {
  nicknameError.textContent = data.error;
});

socket.on("nickname_ok", (data) => {
  myNickname = data.nickname;
  nicknameError.textContent = "";
  myNicknameLabel.textContent = myNickname;
  gate.classList.add("hidden");
  app.classList.remove("hidden");
});

// ---------- Rooms ----------
newRoomForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const room = newRoomInput.value.trim();
  if (!room) return;
  socket.emit("join_room_event", { room });
  newRoomInput.value = "";
});

socket.on("room_list", (rooms) => {
  roomList.innerHTML = "";
  rooms.forEach((room) => {
    const li = document.createElement("li");
    li.className = currentIsRoom && currentChannel === room ? "active" : "";
    li.innerHTML = `<span class="ch-code">#</span><span>${escapeHtml(room)}</span>`;
    li.addEventListener("click", () => {
      socket.emit("join_room_event", { room });
    });
    roomList.appendChild(li);
  });
});

socket.on("room_history", (data) => {
  currentChannel = data.channel;
  currentIsRoom = true;
  currentDmPartner = null;
  renderChannelHeader();
  renderHistory(data.messages);
  highlightActiveRoom();
});

socket.on("new_message", (msg) => {
  if (currentIsRoom && msg.channel === currentChannel) {
    appendMessage(msg);
  }
});

// ---------- Users / DMs ----------
socket.on("user_list", (users) => {
  onlineCount.textContent = users.length;
  userList.innerHTML = "";
  users.forEach((nick) => {
    const li = document.createElement("li");
    const isMe = nick === myNickname;
    li.innerHTML = `<span class="status-dot"></span><span>${escapeHtml(nick)}${isMe ? " (you)" : ""}</span>`;
    if (!isMe) {
      li.addEventListener("click", () => {
        socket.emit("start_dm", { nickname: nick });
      });
    }
    userList.appendChild(li);
  });
});

socket.on("dm_history", (data) => {
  currentChannel = data.channel;
  currentIsRoom = false;
  currentDmPartner = data.with;
  renderChannelHeader();
  renderHistory(data.messages);
  highlightActiveRoom();
});

socket.on("new_dm", (msg) => {
  if (!currentIsRoom && msg.channel === currentChannel) {
    appendMessage(msg);
  }
});

// ---------- Sending messages ----------
messageForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  socket.emit("send_message", { text });
  messageInput.value = "";
});

// ---------- Rendering ----------
function renderChannelHeader() {
  if (currentIsRoom) {
    channelCode.textContent = "CH // ROOM";
    channelTitle.textContent = currentChannel;
  } else {
    channelCode.textContent = "CH // DIRECT";
    channelTitle.textContent = currentDmPartner;
  }
}

function renderHistory(messages) {
  messageList.innerHTML = "";
  messages.forEach(appendMessage);
}

function appendMessage(msg) {
  const div = document.createElement("div");
  const mine = msg.sender === myNickname;
  div.className = `msg ${mine ? "mine" : "theirs"}`;
  const time = formatTime(msg.timestamp);
  div.innerHTML = `
    <span class="msg-meta">${mine ? "" : escapeHtml(msg.sender) + " · "}${time}</span>
    <span class="msg-bubble">${escapeHtml(msg.text)}</span>
  `;
  messageList.appendChild(div);
  messageList.scrollTop = messageList.scrollHeight;
}

function highlightActiveRoom() {
  [...roomList.children].forEach((li) => {
    const label = li.textContent.replace("#", "").trim();
    li.classList.toggle("active", currentIsRoom && label === currentChannel);
  });
}

function formatTime(isoString) {
  const d = new Date(isoString + "Z");
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
