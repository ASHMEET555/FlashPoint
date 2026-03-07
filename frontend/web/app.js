/* ═══════════════════════════════════════════════════════════════
   FLASHPOINT — app.js
   Steps implemented:
     4. SSE live feed — newest card prepended at top with slide-in
     5. Proportional map hotspots (frequency) + rolling bias meter (last 50)
     6. SSE streaming chat — typing effect via token chunks
════════════════════════════════════════════════════════════════ */

"use strict";

// ── Config ────────────────────────────────────────────────────────────
const API_BASE      = "";          // Same origin — served by FastAPI
const SSE_FEED_URL  = `${API_BASE}/v1/feed/stream`;
const CHAT_URL      = `${API_BASE}/v1/chat`;
const REPORT_URL    = `${API_BASE}/v1/generate_report`;
const REPORT_PDF_URL = `${API_BASE}/v1/generate_report/pdf`;
const COMMODITY_URL  = `${API_BASE}/api/commodities/latest`;
const CONFLICTS_URL  = `${API_BASE}/api/conflicts/all`;

// ── State ─────────────────────────────────────────────────────────────
let feedItems    = [];              // Full ordered array, newest last
let chatMessages = [];              // {role, content}
let latestReport = null;
let map, markerLayer;
let conflictMarkers = [];           // Store conflict markers for updates

// Hotspot frequency counter: place → count
const locationFreq = {};

// ── STEP 4 / 5 DUMMY DATA for offline testing ─────────────────────────
// Remove this block and the USE_DUMMY flag when the backend is live.
const USE_DUMMY = false;   // ← flip to true to test without backend
const DUMMY_FEED = [
  { source:"UA Intel Feed", bias:"State-Media (UA)", text:"BREAKING: Large Russian armoured column crossing into Zaporizhzhia. Ukrainian forces report contact.", lat:47.8388, lon:35.1396, place:"Zaporizhzhia" },
  { source:"Reuters",       bias:"Western/Global",   text:"Pentagon confirms Patriot systems dispatched to Kyiv following overnight drone barrage.", lat:50.4501, lon:30.5234, place:"Kyiv" },
  { source:"TASS",          bias:"State-Media (RU)", text:"Russian MoD: 'Routine exercise' concluded near Kherson. All objectives met.", lat:46.6354, lon:32.6169, place:"Kherson" },
  { source:"Times of Israel",bias:"Western/Global",  text:"IDF strikes Hezbollah command node in Beirut. Casualty figures unconfirmed.", lat:33.8886, lon:35.4955, place:"Beirut" },
  { source:"Al Jazeera",   bias:"Neutral/Global",   text:"Gaza ceasefire talks collapse in Cairo. Hamas delegation walks out.", lat:31.5, lon:34.466, place:"Gaza" },
  { source:"CGTN",          bias:"State-Media (CN)", text:"PLA Navy live-fire drill in Taiwan Strait, 40 km from median line.", lat:24.2, lon:120.0, place:"Taiwan" },
  { source:"Yonhap",        bias:"Western/Global",   text:"North Korea fires two ballistic missiles into East Sea. Tokyo issues J-Alert.", lat:40.3399, lon:127.5101, place:"North Korea" },
  { source:"Kyiv Post",     bias:"Western/Global",   text:"Massive cyberattack hits Ukrainian power grid. Ukrenergo reports Kharkiv outages.", lat:49.9935, lon:36.2304, place:"Kharkiv" },
  { source:"Reuters",       bias:"Western/Global",   text:"UN Security Council emergency session on Gaza opens.", lat:40.7489, lon:-73.968, place:"United Nations" },
  { source:"AP",            bias:"Western/Global",   text:"Iran announces 60% uranium enrichment at Fordow. IAEA inspectors denied access.", lat:32.4279, lon:53.688, place:"Iran" },
  { source:"UA Intel Feed", bias:"State-Media (UA)", text:"Kyiv: 34 of 41 Shahed-136 drones shot down. Residential district hit.", lat:50.4501, lon:30.5234, place:"Kyiv" },
  { source:"TASS",          bias:"State-Media (RU)", text:"Moscow warns of proportional response after ATACMS strike on Belgorod depot.", lat:55.7558, lon:37.6173, place:"Moscow" },
];


/* ═══════════════════════════════════════════════════════════════
   UTC CLOCK
════════════════════════════════════════════════════════════════ */
function updateClock() {
  const el = document.getElementById("utc-clock");
  if (!el) return;
  const now = new Date();
  el.textContent = [
    String(now.getUTCHours()).padStart(2,"0"),
    String(now.getUTCMinutes()).padStart(2,"0"),
    String(now.getUTCSeconds()).padStart(2,"0"),
  ].join(":") + " UTC";
}
setInterval(updateClock, 1000);
updateClock();


/* ═══════════════════════════════════════════════════════════════
   STEP 4 — LIVE FEED via SSE (newest at top)
════════════════════════════════════════════════════════════════ */
function biasClass(bias) {
  if (!bias) return "";
  if (/Russia|State-Media\s*\(RU\)/i.test(bias) || /China|State-Media\s*\(CN\)/i.test(bias)) return "alert-card";
  return "";
}

function buildFeedCard(item, isNew = false) {
  const bias   = item.bias   || "Neutral";
  const src    = item.source || "UNKNOWN";
  const text   = item.text   || "";
  const place  = item.place  ? ` • ${item.place}` : "";
  const cls    = `cyber-card ${biasClass(bias)}${isNew ? " feed-card--new" : ""}`.trim();

  const card = document.createElement("div");
  card.className = cls;
  card.innerHTML = `
    <div class="feed-source">${src} &bull; <span class="bias-tag">${bias}</span>${place}</div>
    <div class="feed-text">${text}</div>
  `;
  return card;
}

function prependFeedCard(item) {
  const container = document.getElementById("feed-container");

  // Remove placeholder if present
  const ph = container.querySelector(".feed-placeholder");
  if (ph) ph.remove();

  const card = buildFeedCard(item, true);
  container.insertBefore(card, container.firstChild);

  // Remove "new" flash class after animation completes
  setTimeout(() => card.classList.remove("feed-card--new"), 1200);
}

function initFeedSSE() {
  if (USE_DUMMY) {
    // Inject dummy data with staggered timing to simulate stream
    DUMMY_FEED.forEach((item, i) => {
      setTimeout(() => {
        feedItems.push(item);
        prependFeedCard(item);
        accumulateLocation(item);
        updateMapMarkers();
      }, i * 400);
    });
    return;
  }

  const es = new EventSource(SSE_FEED_URL);

  es.onmessage = (e) => {
    if (!e.data || e.data.startsWith(":")) return;   // keep-alive
    try {
      const item = JSON.parse(e.data);
      feedItems.push(item);
      prependFeedCard(item);
      accumulateLocation(item);
      updateMapMarkers();
    } catch (_) { /* malformed JSON — ignore */ }
  };

  es.onerror = () => {
    console.warn("SSE connection lost, will auto-reconnect…");
  };
}


/* ═══════════════════════════════════════════════════════════════
   STEP 5 — LEAFLET MAP with proportional hotspots
════════════════════════════════════════════════════════════════ */
function initMap() {
  map = L.map("map", { zoomControl: true, attributionControl: false }).setView([20, 0], 2);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
  }).addTo(map);
  markerLayer = L.layerGroup().addTo(map);
}

function markerColor(bias) {
  if (!bias) return "#22c55e";
  if (/Russia|State-Media\s*\(RU\)|Eastern/i.test(bias) || /China|State-Media\s*\(CN\)/i.test(bias)) return "#ef4444";
  if (/Western|US\/|UK\/|NATO/i.test(bias)) return "#0ea5e9";
  return "#22c55e";
}

/** Track cumulative mention count per place for proportional radius. */
function accumulateLocation(item) {
  if (item.place) {
    locationFreq[item.place] = (locationFreq[item.place] || 0) + 1;
  }
}

function updateMapMarkers() {
  if (!markerLayer) return;
  markerLayer.clearLayers();

  // Build one marker per unique location from the full feed
  const seen = new Set();

  // Iterate newest-first so most-recent bias wins for colour
  for (let i = feedItems.length - 1; i >= 0; i--) {
    const item = feedItems[i];
    if (item.lat == null || item.lon == null) continue;

    const key = item.place || `${item.lat},${item.lon}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const freq  = locationFreq[key] || 1;
    // Radius: base 6 + up to 14 extra, scaled logarithmically
    const radius = 6 + Math.min(14, Math.log2(freq + 1) * 4);
    const color  = markerColor(item.bias);
    const popup  = `<b>${item.place || item.source}</b><br>
                    Mentions: <b>${freq}</b><br>
                    ${(item.text || "").slice(0, 120)}…`;

    L.circleMarker([item.lat, item.lon], {
      radius,
      color,
      fillColor: color,
      fillOpacity: 0.65,
      weight: 1.5,
    })
      .bindPopup(popup)
      .bindTooltip(`${item.place || item.source} (×${freq})`)
      .addTo(markerLayer);
  }
}

initMap();


/* ═══════════════════════════════════════════════════════════════
   REPORT GENERATION
════════════════════════════════════════════════════════════════ */
document.getElementById("generate-report-btn").addEventListener("click", async () => {
  const btn = document.getElementById("generate-report-btn");
  btn.textContent = "⏳ GENERATING SITREP...";
  btn.disabled = true;

  try {
    let report;
    if (USE_DUMMY) {
      await new Promise(r => setTimeout(r, 1000));
      report = `FLASHPOINT SITREP — ${new Date().toISOString().slice(0,16).replace("T"," ")} UTC\n\nSITUATION OVERVIEW:\nMultiple active flashpoints confirmed across Eastern Europe, Middle East, and East Asia.\n\nKEY DEVELOPMENTS:\n• Russian armoured column crosses into Zaporizhzhia [UA Intel Feed]\n• IDF strikes Beirut command node [Times of Israel]\n• PLA Navy live-fire drill 40km from Taiwan median line [CGTN]\n\nOUTLOOK:\nInformation environment highly contested. Recommend sustained monitoring.`;
    } else {
      const res = await fetch(REPORT_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      report = (await res.json()).report;
    }

    latestReport = report;
    document.getElementById("report-preview").value = report;
    document.getElementById("report-section").classList.remove("hidden");
  } catch (e) {
    alert(`⚠️ Report Error: ${e.message}`);
  } finally {
    btn.textContent = "GENERATE REPORT";
    btn.disabled = false;
  }
});

document.getElementById("download-pdf-btn").addEventListener("click", async () => {
  const btn = document.getElementById("download-pdf-btn");
  btn.textContent = "⏳ BUILDING PDF...";
  btn.disabled = true;

  try {
    if (USE_DUMMY) {
      // Offline: build a minimal PDF client-side for demo purposes
      const ts   = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
      const blob = new Blob(
        [`%PDF-1.4\n% dummy PDF placeholder — run backend for full SITREP\n`],
        { type: "application/pdf" },
      );
      const a    = Object.assign(document.createElement("a"), {
        href: URL.createObjectURL(blob),
        download: `SITREP_${ts}.pdf`,
      });
      a.click();
      URL.revokeObjectURL(a.href);
    } else {
      // Live: stream the server-rendered PDF directly as a file download
      const res = await fetch(REPORT_PDF_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob     = await res.blob();
      const filename = (res.headers.get("Content-Disposition") || "")
        .match(/filename="?([^"]+)"?/)?.[1] ?? "SITREP.pdf";
      const a = Object.assign(document.createElement("a"), {
        href: URL.createObjectURL(blob),
        download: filename,
      });
      a.click();
      URL.revokeObjectURL(a.href);
    }
  } catch (e) {
    alert(`⚠️ PDF Error: ${e.message}`);
  } finally {
    btn.textContent = "⬇ DOWNLOAD PDF";
    btn.disabled = false;
  }
});


/* ═══════════════════════════════════════════════════════════════
   STEP 6 — INTEL CHAT with SSE streaming typing effect
════════════════════════════════════════════════════════════════ */
function appendBubble(role, content = "") {
  const history = document.getElementById("chat-history");
  const bubble  = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = content;
  history.appendChild(bubble);
  history.scrollTop = history.scrollHeight;
  return bubble;
}

async function sendChatSSE(message) {
  if (USE_DUMMY) {
    // Simulate streaming with character-by-character output
    const mock = `[DUMMY INTEL] Query: "${message}"\n\nBased on current feed:\n• Multiple active flashpoints confirmed.\n• Narrative divergence detected across Western and Eastern sources.\n• Recommend cross-referencing before escalation.`;
    return mock;
  }

  const res = await fetch(CHAT_URL, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ message, history: chatMessages.slice(-6) }),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  // Stream response is an SSE body — read it as a stream
  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let   buffer  = "";
  let   full    = "";

  return { reader, decoder, getBuffer: () => buffer, setBuffer: (b) => { buffer = b; }, append: (t) => { full += t; }, getFull: () => full };
}

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const query = input.value.trim();
  if (!query) return;

  input.value   = "";
  input.disabled = true;

  chatMessages.push({ role: "user", content: query });
  appendBubble("user", query);

  const thinkBubble = appendBubble("thinking", "🔄 Analyzing secure channels…");

  try {
    if (USE_DUMMY) {
      // Character-by-character fake stream
      const mock = `[DUMMY INTEL] Query: "${query}"\n\nBased on current feed:\n• Multiple active flashpoints confirmed.\n• Narrative divergence detected across Western and Eastern sources.\n• Recommend cross-referencing before escalation.`;
      thinkBubble.className = "chat-bubble assistant";
      thinkBubble.textContent = "";
      let i = 0;
      await new Promise(resolve => {
        const tick = setInterval(() => {
          thinkBubble.textContent += mock[i++];
          document.getElementById("chat-history").scrollTop = 9999;
          if (i >= mock.length) { clearInterval(tick); resolve(); }
        }, 18);
      });
      chatMessages.push({ role: "assistant", content: mock });
    } else {
      // Real SSE streaming from backend
      const res = await fetch(CHAT_URL, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message: query, history: chatMessages.slice(-6) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      thinkBubble.className   = "chat-bubble assistant";
      thinkBubble.textContent = "";

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buf     = "";
      let   full    = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        let backendError = null;
    for (const line of lines) {
  if (!line.startsWith("data: ")) continue;
  const payload = line.slice(6).trim();
  if (payload === "[DONE]") break;
  
  let streamError = null; // Extract error variable outside the try block
  
  try {
    const obj = JSON.parse(payload);
    if (obj.token) {
      full += obj.token;
      thinkBubble.textContent = full;
      document.getElementById("chat-history").scrollTop = 9999;
    }
    if (obj.error) streamError = obj.error; // Assign it instead of throwing
  } catch (_) { /* non-JSON line */ }
  
  // Throw the error OUTSIDE the try/catch block so the UI handles it
  if (streamError) throw new Error(streamError);
}
// Throw the error outside the try/catch block so the outer catch can handle it
if (backendError) throw new Error(backendError);
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();   // keep partial last line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") break;
          try {
            const obj = JSON.parse(payload);
            if (obj.token) {
              full += obj.token;
              thinkBubble.textContent = full;
              document.getElementById("chat-history").scrollTop = 9999;
            }
            if (obj.error) throw new Error(obj.error);
          } catch (_) { /* non-JSON line */ }
        }
      }

      chatMessages.push({ role: "assistant", content: full });
    }
  } catch (err) {
    thinkBubble.className   = "chat-bubble assistant";
    thinkBubble.textContent = `⚠️ System Error: ${err.message}`;
  } finally {
    input.disabled = false;
    input.focus();
  }
});


/* ═══════════════════════════════════════════════════════════════
   COMMODITY PRICES
════════════════════════════════════════════════════════════════ */

const COMMODITY_NAMES = {
  "XAU": "Gold",
  "XAG": "Silver",
  "WTIOIL-FUT": "WTI Crude",
  "BRENTOIL-FUT": "Brent Crude"
};

let lastCommodityData = null;

async function fetchCommodityPrices() {
  try {
    const response = await fetch(COMMODITY_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    const data = await response.json();
    lastCommodityData = data;
    
    renderCommodityPrices(data);
  } catch (err) {
    console.error("Commodity fetch error:", err);
    document.getElementById("commodity-grid").innerHTML = 
      '<div class="commodity-loading" style="color:#ff3366;">⚠️ Failed to load prices</div>';
  }
}

function renderCommodityPrices(data) {
  const grid = document.getElementById("commodity-grid");
  const footer = document.getElementById("commodity-footer");
  
  if (!data.success || !data.prices) {
    grid.innerHTML = '<div class="commodity-loading">No data available</div>';
    return;
  }
  
  const prices = data.prices;
  let html = "";
  
  for (const [symbol, info] of Object.entries(prices)) {
    const name = COMMODITY_NAMES[symbol] || symbol;
    const rate = parseFloat(info.rate || 0);
    const unit = info.unit || "USD";
    const change = parseFloat(info.change_24h || 0);
    
    // Determine change direction
    let changeClass = "neutral";
    let changeIcon = "●";
    if (change > 0.5) {
      changeClass = "up";
      changeIcon = "▲";
    } else if (change < -0.5) {
      changeClass = "down";
      changeIcon = "▼";
    }
    
    const changeText = change !== 0 
      ? `${changeIcon} ${change > 0 ? "+" : ""}${change.toFixed(2)}%` 
      : "● No change";
    
    html += `
      <div class="commodity-card">
        <div class="commodity-name">${name}</div>
        <div class="commodity-price">$${rate.toFixed(2)}</div>
        <div class="commodity-change ${changeClass}">${changeText}</div>
        <div class="commodity-meta">${unit} • ${symbol}</div>
      </div>
    `;
  }
  
  grid.innerHTML = html;
  
  // Update footer
  const lastUpdate = data.metadata?.cache_time 
    ? new Date(data.metadata.cache_time).toLocaleTimeString('en-US', { hour12: false })
    : "Unknown";
  
  const cacheStatus = data.metadata?.from_cache ? "CACHED" : "LIVE";
  const cacheColor = data.metadata?.from_cache ? "#ffd700" : "#00ff88";
  
  footer.innerHTML = `
    <span class="text-muted" style="font-size:0.7rem;">
      Last: ${lastUpdate} • 
      <span style="color:${cacheColor}">●</span> ${cacheStatus}
    </span>
  `;
}

// Poll commodities every 5 minutes
setInterval(fetchCommodityPrices, 5 * 60 * 1000);


/* ═══════════════════════════════════════════════════════════════
   CONFLICT MARKERS
════════════════════════════════════════════════════════════════ */

async function fetchConflicts() {
  try {
    const response = await fetch(CONFLICTS_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    const data = await response.json();
    
    if (data.success && data.conflicts) {
      renderConflictMarkers(data.conflicts);
    }
  } catch (err) {
    console.error("Conflicts fetch error:", err);
  }
}

function renderConflictMarkers(conflicts) {
  if (!map) return;
  
  // Clear existing conflict markers
  conflictMarkers.forEach(marker => marker.remove());
  conflictMarkers = [];
  
  conflicts.forEach(conflict => {
    if (!conflict.coordinates?.lat || !conflict.coordinates?.lng) return;
    
    const { lat, lng } = conflict.coordinates;
    const severity = conflict.severity || 5;
    const impact = conflict.impact || "Limited";
    
    // Color by impact
    let color = "#00ff88"; // Green for Limited
    if (impact === "Critical") color = "#ff3366";
    else if (impact === "Significant") color = "#ffd700";
    
    // Size by severity (1-10 scale)
    const radius = 5 + (severity * 2);
    
    // Create circle marker
    const marker = L.circleMarker([lat, lng], {
      radius: radius,
      fillColor: color,
      color: "#1a1a1a",
      weight: 2,
      opacity: 1,
      fillOpacity: 0.7
    });
    
    // Popup content
    const popupContent = `
      <div style="min-width:200px;">
        <strong style="color:#cc0000;">${conflict.name}</strong><br/>
        <span style="color:#555;">Status:</span> ${conflict.status}<br/>
        <span style="color:#555;">Impact:</span> <strong>${impact}</strong><br/>
        <span style="color:#555;">Severity:</span> ${severity}/10<br/>
        ${conflict.description ? `<p style="margin-top:8px; font-size:0.7rem;">${conflict.description}</p>` : ""}
      </div>
    `;
    
    marker.bindPopup(popupContent);
    marker.addTo(map);
    
    conflictMarkers.push(marker);
  });
  
  console.log(`✅ Rendered ${conflicts.length} conflict markers`);
}

// Poll conflicts every 5 minutes
setInterval(fetchConflicts, 5 * 60 * 1000);


/* ═══════════════════════════════════════════════════════════════
   BOOT
════════════════════════════════════════════════════════════════ */
fetchCommodityPrices();  // Initial fetch
fetchConflicts();        // Initial fetch
initFeedSSE();

