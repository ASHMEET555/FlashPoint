/**
 * feed.js - Real-time event feed via SSE
 */

import { API_BASE, ENDPOINTS, biasClass, escapeHTML } from './utils.js';
import { updateMapHotspot } from './map.js';

let feedItems = [];
let eventSource = null;

/**
 * Build a feed card DOM element
 */
function buildFeedCard(item, isNew = false) {
    const bias = item.bias || "Neutral";
    const src = item.source || "UNKNOWN";
    const text = item.text || "";
    const place = item.place ? ` • ${item.place}` : "";
    const cls = `cyber-card ${biasClass(bias)}${isNew ? " feed-card--new" : ""}`.trim();

    const card = document.createElement("div");
    card.className = cls;
    card.innerHTML = `
        <div class="feed-source">${escapeHTML(src)} &bull; <span class="bias-tag">${escapeHTML(bias)}</span>${escapeHTML(place)}</div>
        <div class="feed-text">${escapeHTML(text)}</div>
    `;
    return card;
}

/**
 * Prepend new event card to feed (newest at top)
 */
function prependFeedCard(item) {
    const container = document.getElementById("feed-container");
    if (!container) return;

    // Remove placeholder if present
    const ph = container.querySelector(".feed-placeholder");
    if (ph) ph.remove();

    const card = buildFeedCard(item, true);
    container.insertBefore(card, container.firstChild);

    // Trigger slide-in animation
    setTimeout(() => card.classList.remove("feed-card--new"), 10);

    // Limit displayed cards to 100
    const cards = container.querySelectorAll(".cyber-card");
    if (cards.length > 100) {
        cards[cards.length - 1].remove();
    }

    feedItems.unshift(item);
}

/**
 * Load initial events from PostgreSQL
 */
async function loadInitialEvents() {
    try {
        const resp = await fetch(`${API_BASE}${ENDPOINTS.events_recent}?limit=50`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Failed to load events");

        const container = document.getElementById("feed-container");
        if (!container) return;

        container.innerHTML = ""; // Clear placeholder

        // Render in reverse (oldest first, newest at top)
        data.events.reverse().forEach(event => {
            const card = buildFeedCard(event);
            container.appendChild(card);
            feedItems.push(event);
        });

        console.log(`✅ Loaded ${data.count} initial events`);
        
    } catch (err) {
        console.error("Failed to load initial events:", err);
        document.getElementById("feed-container").innerHTML = `
            <div class="cyber-card alert-card">
                <strong>⚠️ Feed Offline</strong><br>
                Unable to load events: ${err.message}
            </div>
        `;
    }
}

/**
 * Initialize SSE connection for real-time updates
 */
function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }

    const url = `${API_BASE}${ENDPOINTS.events_stream}`;
    eventSource = new EventSource(url);

    eventSource.onopen = () => {
        console.log("✅ SSE connected");
    };

    eventSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            
            // Ignore initial snapshot (already loaded via REST)
            if (feedItems.some(item => item.id === data.id)) {
                return;
            }

            prependFeedCard(data);
            
            // Update map hotspot
            updateMapHotspot(data);
            
        } catch (err) {
            console.error("SSE parse error:", err, e.data);
        }
    };

    eventSource.onerror = (err) => {
        console.error("❌ SSE error:", err);
        eventSource.close();
        
        // Reconnect after 5 seconds
        setTimeout(() => {
            console.log("🔄 Reconnecting SSE...");
            connectSSE();
        }, 5000);
    };
}

/**
 * Initialize feed module
 */
export function initFeed() {
    console.log("📡 Initializing feed...");
    loadInitialEvents().then(() => {
        connectSSE();
    });
}

/**
 * Get current feed items
 */
export function getFeedItems() {
    return feedItems;
}

/**
 * Cleanup
 */
export function disconnectFeed() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}
