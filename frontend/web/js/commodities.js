/**
 * commodities.js - Real-time commodity price tracker
 */

import { API_BASE, ENDPOINTS, escapeHTML } from './utils.js';

let lastPrices = {};

/**
 * Render commodity prices
 */
function renderCommodityPrices(prices) {
    const container = document.getElementById("commodities-container");
    if (!container) return;

    container.innerHTML = "";

    if (!prices || prices.length === 0) {
        container.innerHTML = `<div class="commodity-item">No data available</div>`;
        return;
    }

    prices.forEach(item => {
        const symbol = item.symbol || "???";
        const rate = item.rate !== undefined ? item.rate.toFixed(2) : "N/A";
        const unit = item.unit || "";
        const change24h = item.change_24h || 0;
        
        const changeClass = change24h >= 0 ? "commodity-up" : "commodity-down";
        const changeIcon = change24h >= 0 ? "▲" : "▼";
        const changeText = Math.abs(change24h).toFixed(2);

        const div = document.createElement("div");
        div.className = "commodity-item";
        div.innerHTML = `
            <div class="commodity-symbol">${escapeHTML(symbol)}</div>
            <div class="commodity-price">$${rate} <span class="commodity-unit">${escapeHTML(unit)}</span></div>
            <div class="commodity-change ${changeClass}">
                ${changeIcon} ${changeText}%
            </div>
        `;
        container.appendChild(div);

        lastPrices[symbol] = rate;
    });
}

/**
 * Fetch commodity prices from API
 */
async function fetchCommodityPrices() {
    try {
        const resp = await fetch(`${API_BASE}${ENDPOINTS.commodities}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        if (data.success && data.commodities) {
            renderCommodityPrices(data.commodities);
            console.log("✅ Updated commodity prices");
        }

    } catch (err) {
        console.error("Failed to fetch commodities:", err);
        const container = document.getElementById("commodities-container");
        if (container) {
            container.innerHTML = `
                <div class="commodity-item" style="color: #FF4444;">
                    ⚠️ Failed to load prices
                </div>
            `;
        }
    }
}

/**
 * Initialize commodity tracker
 */
export function initCommodities() {
    fetchCommodityPrices();
    
    // Update every 5 minutes
    setInterval(fetchCommodityPrices, 5 * 60 * 1000);
    
    console.log("💰 Commodities tracker initialized");
}
