/**
 * utils.js - Utility functions and constants
 */

export const API_BASE = "";
export const ENDPOINTS = {
    events_stream: "/api/events/stream",
    events_recent: "/api/events/recent",
    chat: "/v1/chat",
    report: "/v1/generate_report",
    report_pdf: "/v1/generate_report/pdf",
    commodities: "/api/commodities/latest",
    conflicts: "/api/conflicts/all"
};

/**
 * Classify bias for visual styling
 */
export function biasClass(bias) {
    if (!bias) return "";
    if (/Russia|State-Media\s*\(RU\)/i.test(bias) || 
        /China|State-Media\s*\(CN\)/i.test(bias)) {
        return "alert-card";
    }
    return "";
}

/**
 * Format UTC time
 */
export function formatUTC() {
    const now = new Date();
    return [
        String(now.getUTCHours()).padStart(2, "0"),
        String(now.getUTCMinutes()).padStart(2, "0"),
        String(now.getUTCSeconds()).padStart(2, "0"),
    ].join(":") + " UTC";
}

/**
 * Update clock display
 */
export function updateClock() {
    const el = document.getElementById("utc-clock");
    if (!el) return;
    el.textContent = formatUTC();
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Show notification toast
 */
export function showNotification(message, type = "info") {
    const container = document.getElementById("notification-container") || createNotificationContainer();
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add("fade-out");
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function createNotificationContainer() {
    const container = document.createElement("div");
    container.id = "notification-container";
    container.style.cssText = "position:fixed;top:20px;right:20px;z-index:10000;";
    document.body.appendChild(container);
    return container;
}
