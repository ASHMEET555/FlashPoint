/**
 * chat.js - RAG-powered chat with streaming responses
 */

import { API_BASE, ENDPOINTS, escapeHTML, showNotification } from './utils.js';

let chatMessages = [];
let isStreaming = false;

/**
 * Append message to chat log
 */
function appendMessage(role, content) {
    const log = document.getElementById("chat-history");
    if (!log) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg chat-msg--${role}`;
    msgDiv.innerHTML = `
        <span class="chat-role">${role === "user" ? "YOU" : "FLASHPOINT"}:</span>
        <span class="chat-content">${escapeHTML(content)}</span>
    `;
    log.appendChild(msgDiv);
    log.scrollTop = log.scrollHeight;

    chatMessages.push({ role, content });
}

/**
 * Stream assistant response token by token
 */
async function streamResponse(userMessage) {
    isStreaming = true;
    const log = document.getElementById("chat-history");
    if (!log) return;

    // Create assistant message container
    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-msg chat-msg--assistant";
    msgDiv.innerHTML = `
        <span class="chat-role">FLASHPOINT:</span>
        <span class="chat-content"></span>
    `;
    log.appendChild(msgDiv);
    const contentSpan = msgDiv.querySelector(".chat-content");

    let fullText = "";

    try {
        const resp = await fetch(`${API_BASE}${ENDPOINTS.chat}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userMessage,
                history: chatMessages.slice(-5) // Last 5 messages for context
            })
        });

        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (!line.trim() || !line.startsWith("data: ")) continue;

                const data = line.slice(6).trim();
                if (data === "[DONE]") {
                    chatMessages.push({ role: "assistant", content: fullText });
                    isStreaming = false;
                    return;
                }

                try {
                    const parsed = JSON.parse(data);
                    
                    if (parsed.error) {
                        contentSpan.textContent += `\n⚠️ Error: ${parsed.error}`;
                        showNotification(parsed.error, "error");
                        break;
                    }

                    if (parsed.token) {
                        fullText += parsed.token;
                        contentSpan.textContent = fullText;
                        log.scrollTop = log.scrollHeight;
                    }
                } catch (e) {
                    console.warn("Failed to parse SSE data:", data);
                }
            }
        }

    } catch (err) {
        console.error("Chat error:", err);
        contentSpan.textContent = `❌ Connection error: ${err.message}`;
        showNotification("Failed to connect to chat service", "error");
    } finally {
        isStreaming = false;
    }
}

/**
 * Handle chat form submission
 */
function handleChatSubmit(e) {
    e.preventDefault();
    if (isStreaming) return;

    const input = document.getElementById("chat-input");
    if (!input) return;

    const message = input.value.trim();
    if (!message) return;

    input.value = "";
    input.disabled = true;

    appendMessage("user", message);
    streamResponse(message).finally(() => {
        input.disabled = false;
        input.focus();
    });
}

/**
 * Initialize chat module
 */
export function initChat() {
    const form = document.getElementById("chat-form");
    if (!form) return;

    form.addEventListener("submit", handleChatSubmit);
    
    // Welcome message
    const log = document.getElementById("chat-history");
    if (log && log.children.length === 0) {
        const welcome = document.createElement("div");
        welcome.className = "chat-msg chat-msg--system";
        welcome.innerHTML = `
            <span class="chat-content">
                <strong>FLASHPOINT Intelligence System</strong><br>
                Ask questions about current geopolitical events, conflicts, or specific regions.<br>
                Type your query below to access the intelligence database.
            </span>
        `;
        log.appendChild(welcome);
    }

    console.log("💬 Chat initialized");
}

/**
 * Get chat history
 */
export function getChatHistory() {
    return chatMessages;
}
