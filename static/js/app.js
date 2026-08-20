// =====================================
// app.js (STABLE + CHAT SESSIONS)
// =====================================

import {
    loadModels,
    loadAgent,
    loadTools,
    sendMessage
} from "./api.js";


// =============================
// STATE
// =============================
const state = {
    model: "",
    agent: "default",
    tool: "none",
    chat: [],
    chats: [],
    activeChatId: null,
    agentAvailable: false
};

// =============================
// STORAGE KEYS
// =============================
const LS_KEY = "ai-studio-chats";
const DB_NAME = "ai-studio-db";
const STORE = "handles";


// =============================
// START
// =============================
document.addEventListener("DOMContentLoaded", init);


// =============================
// INIT APP
// =============================
async function init() {

    console.log("[APP] START");

    await restoreChats();
    await setupAgent();
    await setupModels();
    await setupTools();

    setupSidebarEvents();
    setupEvents();

    console.log("[APP] READY");
}


// =============================
// AGENT AVAILABILITY
// =============================
async function setupAgent() {
    const data = await loadAgent();
    state.agentAvailable = data.available === true;
    console.log("[AGENT]", state.agentAvailable ? "available" : "not available");
}


// =============================
// ELEMENT HELPERS
// =============================
const el = {
    // CHAT
    model: () => document.getElementById("model-select"),
    input: () => document.getElementById("user-input"),
    send: () => document.getElementById("send-btn"),
    toolbox: () => document.getElementById("toolbox"),
    chatList: () => document.getElementById("chat-list"),
    chatWindow: () => document.getElementById("chat-window"),

    // SIDEBAR
    newChat: () => document.getElementById("new-chat-btn"),
    research: () => document.getElementById("research-btn"),
    code: () => document.getElementById("code-btn"),
    file: () => document.getElementById("file-loader")
};


// =============================
// HELPERS
// =============================
function formatTimestamp(ts) {
    const d = new Date(ts || Date.now());
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
           `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function activeChat() {
    return state.chats.find(c => c.id === state.activeChatId) || null;
}


// =============================
// INDEXEDDB (FILE HANDLES)
// =============================
function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = () => {
            if (!req.result.objectStoreNames.contains(STORE)) {
                req.result.createObjectStore(STORE);
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function saveHandle(id, handle) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).put(handle, id);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
    });
}

async function getHandle(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, "readonly");
        const req = tx.objectStore(STORE).get(id);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function deleteHandle(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).delete(id);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
    });
}


// =============================
// LOCAL STORAGE (CHAT METADATA + MESSAGES)
// =============================
function saveChatsMeta() {
    const meta = state.chats.map(c => ({
        id: c.id,
        title: c.title,
        fileName: c.fileName,
        created: c.created,
        messages: c.messages
    }));
    localStorage.setItem(LS_KEY, JSON.stringify(meta));
    console.log("[CHAT] Metadata saved to localStorage", meta.length, "chats");
}

function loadChatsMeta() {
    try {
        return JSON.parse(localStorage.getItem(LS_KEY)) || [];
    } catch (err) {
        console.warn("[CHAT] Could not read localStorage", err);
        return [];
    }
}


// =============================
// CHAT FILE BUILDING / WRITING
// =============================
function buildChatText(chat) {
    const lines = chat.messages.map(m => {
        const ts = formatTimestamp(m.time);
        return m.role === "user"
            ? `[${ts}] USER: ${m.text}`
            : `[${ts}] AI: ${m.text}`;
    });
    const header =
        `AI STUDIO CHAT - ${chat.title}\n` +
        `Created: ${formatTimestamp(chat.created)}\n` +
        `================================================\n`;
    return header + lines.join("\n") + (lines.length ? "\n" : "");
}

async function writeChatFile(chat) {
    if (!chat.handle) {
        console.warn("[CHAT] No file handle for", chat.id, "- skipping file write");
        return;
    }
    const text = buildChatText(chat);
    const writable = await chat.handle.createWritable();
    await writable.write(text);
    await writable.close();
    console.log("[CHAT] File written:", chat.fileName);
}


// =============================
// CREATE NEW CHAT
// =============================
async function createNewChat() {

    console.log("=================================");
    console.log("[CHAT] New Chat Requested");
    console.log("=================================");

    if (!window.showSaveFilePicker) {
        alert("File System Access API not supported in this browser. Use Chrome or Edge.");
        console.error("[CHAT] showSaveFilePicker unavailable");
        return;
    }

    try {
        // Ask the user where to save this chat's text file.
        const handle = await window.showSaveFilePicker({
            suggestedName: `chat-${Date.now()}.txt`,
            types: [
                {
                    description: "Text file",
                    accept: { "text/plain": [".txt"] }
                }
            ]
        });

        const chat = {
            id: crypto.randomUUID(),
            title: "New Chat",
            fileName: handle.name,
            created: Date.now(),
            handle,
            messages: []
        };

        state.chats.push(chat);
        state.activeChatId = chat.id;
        state.chat = chat.messages;

        await saveHandle(chat.id, handle);
        saveChatsMeta();
        await writeChatFile(chat);

        renderChatList();
        renderMessages();

        console.log("[CHAT] Created", { id: chat.id, file: chat.fileName });
    } catch (err) {
        if (err.name !== "AbortError") {
            console.error("[CHAT] Create Failed", err);
        }
    }
}


// =============================
// RENAME CHAT
// =============================
async function renameChat(chatId) {

    const chat = state.chats.find(c => c.id === chatId);
    if (!chat) return;

    console.log("[CHAT] Rename Requested", chat.title);

    const newName = prompt("Rename chat:", chat.title);
    if (newName === null) return;

    const trimmed = newName.trim();
    if (!trimmed) return;

    chat.title = trimmed;
    saveChatsMeta();
    await writeChatFile(chat);
    renderChatList();

    console.log("[CHAT] Renamed", { id: chat.id, title: trimmed });
}


// =============================
// DELETE CHAT
// =============================
async function deleteChat(chatId) {

    const chat = state.chats.find(c => c.id === chatId);
    if (!chat) return;

    console.log("[CHAT] Delete Requested", chat.title);

    if (!confirm(`Delete chat "${chat.title}"?`)) {
        console.log("[CHAT] Delete Cancelled");
        return;
    }

    state.chats = state.chats.filter(c => c.id !== chatId);
    if (state.activeChatId === chatId) {
        state.activeChatId = null;
        state.chat = [];
    }

    saveChatsMeta();
    await deleteHandle(chatId);

    try {
        if (chat.handle && chat.handle.remove) {
            await chat.handle.remove();
            console.log("[CHAT] File deleted:", chat.fileName);
        }
    } catch (err) {
        console.warn("[CHAT] Could not delete file", err);
    }

    renderChatList();
    renderMessages();

    console.log("[CHAT] Deleted", { id: chatId, file: chat.fileName });
}


// =============================
// SELECT CHAT
// =============================
function selectChat(chatId) {

    const chat = state.chats.find(c => c.id === chatId);
    if (!chat) return;

    state.activeChatId = chatId;
    state.chat = chat.messages;

    renderChatList();
    renderMessages();

    console.log("[CHAT] Selected", { id: chat.id, title: chat.title });
}


// =============================
// RENDER CHAT LIST
// =============================
function renderChatList() {

    const list = el.chatList();
    if (!list) return;

    list.innerHTML = "";

    state.chats.forEach(chat => {

        const li = document.createElement("li");
        li.className = "chat-item" + (chat.id === state.activeChatId ? " active" : "");
        li.dataset.id = chat.id;

        const title = document.createElement("span");
        title.className = "chat-title";
        title.textContent = chat.title;
        title.title = chat.fileName;

        const ren = document.createElement("button");
        ren.className = "chat-rename";
        ren.textContent = "✎";
        ren.title = "Rename chat";

        const del = document.createElement("button");
        del.className = "chat-delete";
        del.textContent = "✕";
        del.title = "Delete chat";

        li.appendChild(title);
        li.appendChild(ren);
        li.appendChild(del);

        li.addEventListener("click", () => selectChat(chat.id));

        title.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            renameChat(chat.id);
        });

        ren.addEventListener("click", (e) => {
            e.stopPropagation();
            renameChat(chat.id);
        });

        del.addEventListener("click", (e) => {
            e.stopPropagation();
            deleteChat(chat.id);
        });

        list.appendChild(li);
    });

    console.log("[CHAT] List Rendered:", state.chats.length, "chats");
}


// =============================
// RENDER MESSAGES
// =============================
function renderMessages() {

    const windowEl = el.chatWindow();
    if (!windowEl) return;

    windowEl.innerHTML = "";

    const chat = activeChat();
    if (!chat) return;

    chat.messages.forEach(m => {

        const div = document.createElement("div");
        div.className = "msg " + (m.role === "user" ? "msg-user" : "msg-ai");
        div.textContent = m.text;

        windowEl.appendChild(div);
    });

    windowEl.scrollTop = windowEl.scrollHeight;
}


// =============================
// RESTORE CHATS ON LOAD
// =============================
async function restoreChats() {

    const meta = loadChatsMeta();
    console.log("[CHAT] Restoring", meta.length, "chats");

    for (const m of meta) {

        let handle = null;
        try {
            handle = await getHandle(m.id);
        } catch (err) {
            console.warn("[CHAT] No stored handle for", m.id, err);
        }

        state.chats.push({
            id: m.id,
            title: m.title,
            fileName: m.fileName,
            created: m.created,
            handle,
            messages: m.messages || []
        });
    }

    if (state.chats.length) {
        state.activeChatId = state.chats[0].id;
        state.chat = state.chats[0].messages;
    }

    renderChatList();
    renderMessages();
}


// =============================
// MODELS
// =============================
async function setupModels() {

    const data = await loadModels();

    const select = el.model();

    if (!select) {
        console.error("[MODELS] model-select not found");
        return;
    }

    select.innerHTML = "";

    if (!data.models || data.models.length === 0) {
        console.warn("[MODELS] No models returned from /api/models");
        state.model = "";
        return;
    }

    data.models.forEach(m => {

        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = m.name;

        select.appendChild(opt);
    });

    state.model = data.models[0].id;

    console.log("[MODELS LOADED]");
}


// =============================
// TOOLS
// =============================
async function setupTools() {
    const data = await loadTools();
    const box = el.toolbox();
    if (!box) return;

    box.innerHTML = "";

    if (!state.agentAvailable) {
        box.style.display = "none";
        console.log("[TOOLS] Agent not available - toolbox hidden");
        return;
    }

    box.style.display = "";
    data.tools.forEach(t => {
        const btn = document.createElement("button");
        btn.className = "tool-icon-btn";
        btn.innerHTML = t.icon;
        btn.title = t.name;

        if (!t.enabled) btn.disabled = true;

        btn.addEventListener("click", () => {
            state.tool = t.id;
            console.log("[TOOL SELECTED]", t.id);
            document.querySelectorAll('.tool-icon-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
        box.appendChild(btn);
    });
}


// =============================
// MAIN EVENTS
// =============================
function setupEvents() {

    const sendBtn = el.send();
    const input = el.input();
    const model = el.model();

    if (sendBtn) {
        sendBtn.addEventListener("click", () => {
            console.log("=================================");
            console.log("[BUTTON] Send Clicked");
            console.log("=================================");
            send();
        });
    }

    if (input) {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                console.log("[EVENT] Enter Pressed");
                send();
            }
        });
    }

    if (model) {
        model.addEventListener("change", (e) => {
            state.model = e.target.value;
            console.log("[MODEL]", state.model);
        });
    }
}


// =============================
// SIDEBAR EVENTS
// =============================
function setupSidebarEvents() {

    const newChat = el.newChat();
    const research = el.research();
    const code = el.code();
    const file = el.file();

    if (newChat) {
        newChat.addEventListener("click", () => {
            console.log("=================================");
            console.log("[BUTTON] New Chat Clicked");
            console.log("=================================");
            createNewChat();
        });
    }

    if (research) {
        research.addEventListener("click", () => {
            console.log("=================================");
            console.log("[BUTTON] Research Agent Clicked");
            console.log("=================================");
        });
    }

    if (code) {
        code.addEventListener("click", () => {
            console.log("=================================");
            console.log("[BUTTON] Code Agent Clicked");
            console.log("=================================");
        });
    }

    if (file) {
        file.addEventListener("change", (e) => {
            console.log("=================================");
            console.log("[EVENT] File Loaded");
            console.log("[FILES]", e.target.files);
            console.log("=================================");
        });
    }

    console.log("[SIDEBAR] Events Attached");
}


// =============================
// SEND MESSAGE
// =============================
async function send() {

    const msg = el.input()?.value.trim();
    if (!msg) return;

    console.log("=================================");
    console.log("[SEND] Message Sent");
    console.log("[PAYLOAD]", { message: msg, model: state.model, agent: state.agent, tool: state.tool });
    console.log("=================================");

    let chat = activeChat();

    // No chat yet - create one and ask where to save it.
    if (!chat) {
        console.warn("[SEND] No active chat - creating new chat first");
        await createNewChat();
        chat = activeChat();
        if (!chat) return;
    }

    // History = the stored prior turns (this new message is NOT included yet -
    // the server appends it). Maps {role, text, time} -> {role, content} so the
    // agent can replay the whole conversation into the loop.
    const payload = {
        message: msg,
        model: state.model,
        agent: state.agent,
        tool: state.tool,
        history: chat.messages.map(m => ({ role: m.role, content: m.text }))
    };

    el.input().value = "";

    chat.messages.push({ role: "user", text: msg, time: Date.now() });
    state.chat = chat.messages;
    renderMessages();

    // Disable the Send button while the request is in flight so the user
    // cannot double-send (double sends would only stack up slow LLM requests).
    const sendBtn = el.send();
    if (sendBtn) sendBtn.disabled = true;

    try {
        // POST the message to server.py (/api/chat), which forwards it to
        // chat_bot_agent.py. This can take up to 3 minutes for a local LLM.
        const res = await sendMessage(payload);

        console.log("[AI]", res.reply);

        // Only push the AI bubble when the server actually returned a reply.
        // (res?.reply avoids pushing "undefined" into the chat on failures.)
        const reply = res?.reply ?? "";
        if (reply) {
            chat.messages.push({ role: "ai", text: reply, time: Date.now() });
        } else {
            // Safety net: never store an empty AI turn (it would be replayed
            // into every later prompt). The server already falls back to a
            // readable message, so this should be rare.
            chat.messages.push({
                role: "ai",
                text: "(no reply received - please try again)",
                time: Date.now()
            });
        }
    } catch (err) {
        // The fetch failed (timeout, server down, network). Show the error in
        // the chat window instead of failing silently so the user knows what
        // happened and can retry.
        console.error("[SEND] Failed", err);
        chat.messages.push({
            role: "ai",
            text: `(error: could not reach the server - ${err.message})`,
            time: Date.now()
        });
    } finally {
        // Always re-enable the Send button, whether we got a reply or an error.
        if (sendBtn) sendBtn.disabled = false;
    }

    state.chat = chat.messages;
    renderMessages();

    saveChatsMeta();
    await writeChatFile(chat);

    console.log("[SAVE] Conversation written to", chat.fileName);
}
