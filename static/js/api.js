// api.js - Now with real fetch calls
const API_BASE = "/api";

// Default timeout for FAST endpoints (models/tools just read a JSON file).
const TIMEOUT_MS = 10000;

// Chat replies come from a LOCAL LLM (Ollama) and routinely take 30-60s+ to
// generate. The fast default timeout would abort the request mid-generation,
// so sendMessage uses its own LONG timeout (3 minutes).
const CHAT_TIMEOUT_MS = 180000;

async function fetchWithTimeout(url, options = {}, timeout = TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        return res;
    } finally {
        clearTimeout(timer);
    }
}

export async function loadModels() {
    const res = await fetchWithTimeout(`${API_BASE}/models`);
    return await res.json();
}

export async function loadAgent() {
    const res = await fetchWithTimeout(`${API_BASE}/agent`);
    return await res.json();
}

export async function loadTools() {
    const res = await fetchWithTimeout(`${API_BASE}/tools`);
    return await res.json();
}

export async function sendMessage(payload) {
    // POST the user's message to /api/chat (server.py -> chat_bot_agent.py).
    // Uses the long chat timeout so slow LLM replies are not aborted.
    const res = await fetchWithTimeout(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    }, CHAT_TIMEOUT_MS);
    return await res.json();
}