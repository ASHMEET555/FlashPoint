import { API_BASE, ENDPOINTS, escapeHTML } from './utils.js';

export function initCommodities() {
    fetchCommodityPrices();
    setInterval(fetchCommodityPrices, 5 * 60 * 1000);
}

async function fetchCommodityPrices() {
    const container = document.getElementById("commodity-grid");
    try {
        const resp = await fetch(`${API_BASE}${ENDPOINTS.commodities}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        const raw = json.data || json.prices || {};

        const html = Object.entries(raw)
            .filter(([, v]) => v && v.rate)
            .map(([symbol, info]) => `
                <div class="commodity-card">
                    <div class="commodity-name">${escapeHTML(info.name || symbol)}</div>
                    <div class="commodity-price">$${parseFloat(info.rate).toFixed(2)}</div>
                    <div class="commodity-meta">${escapeHTML(info.unit || "USD")} • ${escapeHTML(symbol)}</div>
                </div>
            `).join("");

        if (container) container.innerHTML = html || "<div class='commodity-loading'>No data</div>";

        const footer = document.getElementById("commodity-footer");
        if (footer) footer.innerHTML = `<span class="text-muted" style="font-size:0.7rem;">
            Last updated: ${new Date().toLocaleTimeString("en-US", {hour12:false})}
        </span>`;

    } catch (err) {
        console.error("Commodity error:", err);
        if (container) container.innerHTML = `<div style="color:#ff4444;">⚠️ ${err.message}</div>`;
    }
}
