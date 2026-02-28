/* ═══════════════════════════════════════════════════════════════
   FLASHPOINT — app.js
   Client-side logic.  Backend calls are stubbed with mock data.
════════════════════════════════════════════════════════════════ */

"use strict";

// ── Config ──────────────────────────────────────────────────────
const API_BASE = "http://localhost:";
const FEED_PORT   = 8000;
const INTEL_PORT  = 8011;
const FEED_POLL_MS = 2000;

// ── State ────────────────────────────────────────────────────────
let feedItems    = [];
let chatMessages = [];   // {role: "user"|"assistant", content: string}
let latestReport = null;
let map, markerLayer;

// ── Mock feed data (replace with real API call when backend ready) ──
const MOCK_FEED = [
  { source: "Reuters", bias: "Western", text: "NATO forces reposition along eastern flank amid rising tensions.", lat: 52.2, lon: 21.0 },
  { source: "RT",      bias: "Russia",  text: "Russian MoD reports successful defensive operations in Kherson region.", lat: 46.6, lon: 32.6 },
  { source: "Al Jazeera", bias: "Neutral", text: "UN Security Council meets for emergency session on ceasefire proposal.", lat: 40.7, lon: -74.0 },
  { source: "CGTN",   bias: "China",   text: "China urges all parties to engage in diplomatic dialogue immediately.", lat: 39.9, lon: 116.4 },
  { source: "BBC",    bias: "Western", text: "Satellite imagery shows troop build-up near contested border zone.", lat: 50.4, lon: 30.5 },
  { source: "Tass",   bias: "Russia",  text: "Western sanctions described as economic warfare by FM Lavrov.", lat: 55.7, lon: 37.6 },
];


/* ═══════════════════════════════════════════════════════════════
   UTC CLOCK
════════════════════════════════════════════════════════════════ */
function updateClock() {
  const el = document.getElementById("utc-clock");
  if (!el) return;
  const now = new Date();
  const hh = String(now.getUTCHours()).padStart(2, "0");
  const mm = String(now.getUTCMinutes()).padStart(2, "0");
  const ss = String(now.getUTCSeconds()).padStart(2, "0");
  el.textContent = `${hh}:${mm}:${ss} UTC`;
}

setInterval(updateClock, 1000);
updateClock();


/* ═══════════════════════════════════════════════════════════════
   NARRATIVE BALANCE
════════════════════════════════════════════════════════════════ */
function calculateBalance(items) {
  const total = items.length;
  if (total === 0) return { west: 50, neutral: 0, east: 50 };

  const westCount    = items.filter(i => (i.bias || "").includes("Western") || (i.bias || "").includes("US")).length;
  const eastCount    = items.filter(i => (i.bias || "").includes("Russia") || (i.bias || "").includes("China") || (i.bias || "").includes("Eastern")).length;
  const neutralCount = total - westCount - eastCount;

  return {
    west:    Math.round((westCount    / total) * 100),
    neutral: Math.round((neutralCount / total) * 100),
    east:    Math.round((eastCount    / total) * 100),
  };
}

function updateBalanceBar(items) {
  const { west, neutral, east } = calculateBalance(items);

  const barWest    = document.getElementById("bar-west");
  const barNeutral = document.getElementById("bar-neutral");
  const barEast    = document.getElementById("bar-east");

  barWest.style.width    = `${west}%`;
  barNeutral.style.width = `${neutral}%`;
  barEast.style.width    = `${east}%`;

  barWest.textContent    = west    > 5 ? `${west}%`    : "";
  barNeutral.textContent = neutral > 5 ? `${neutral}%` : "";
  barEast.textContent    = east    > 5 ? `${east}%`    : "";

  // Update marquee narration label
  const el = document.getElementById("marquee-narration");
  if (!el) return;
  if (west - east > 30 || west > 50)       el.textContent = "WEST";
  else if (east - west > 30 || east > 50)  el.textContent = "EAST";
  else                                      el.textContent = "STABLE";
}


/* ═══════════════════════════════════════════════════════════════
   LIVE FEED
════════════════════════════════════════════════════════════════ */

/**
 * Fetches feed from backend.
 * TODO: Replace mock with:
 *   const res = await fetch(`${API_BASE}${FEED_PORT}/v1/frontend/feed`);
 *   return res.ok ? await res.json() : [];
 */
async function fetchFeed() {
  // --- MOCK ---
  return [...MOCK_FEED];
  // --- END MOCK ---
}

function buildFeedCard(item) {
  const bias  = item.bias  || "Neutral";
  const src   = item.source || "UNKNOWN";
  const text  = item.text   || "";
  const isAlert = bias.includes("Russia") || bias.includes("China");

  const card = document.createElement("div");
  card.className = `cyber-card${isAlert ? " alert-card" : ""}`;
  card.innerHTML = `
    <div class="feed-source">${src} &bull; ${bias}</div>
    <div class="feed-text">${text}</div>
  `;
  return card;
}

async function refreshFeed() {
  const items = await fetchFeed();
  feedItems = items;

  const container = document.getElementById("feed-container");
  // Clear placeholder on first real data
  const placeholder = container.querySelector(".feed-placeholder");
  if (placeholder && items.length) placeholder.remove();

  // Re-render (newest first)
  const reversed = [...items].reverse();

  // Only update DOM nodes that changed (simple approach: rebuild)
  container.innerHTML = "";
  if (!reversed.length) {
    container.innerHTML = `<div class="feed-placeholder text-muted">⏳ Waiting for data stream...</div>`;
  } else {
    reversed.forEach(item => container.appendChild(buildFeedCard(item)));
  }

  updateBalanceBar(items);
  updateMapMarkers(items);
}

// Poll feed every 2 s
refreshFeed();
setInterval(refreshFeed, FEED_POLL_MS);


/* ═══════════════════════════════════════════════════════════════
   LEAFLET MAP
════════════════════════════════════════════════════════════════ */
function initMap() {
  map = L.map("map", { zoomControl: true, attributionControl: false }).setView([20, 0], 2);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors © CARTO",
  }).addTo(map);

  markerLayer = L.layerGroup().addTo(map);
}

function markerColor(bias) {
  if (!bias) return "#22c55e";
  if (bias.includes("Russia") || bias.includes("China") || bias.includes("Eastern")) return "#ef4444";
  if (bias.includes("Western") || bias.includes("US")) return "#0ea5e9";
  return "#22c55e";
}

function updateMapMarkers(items) {
  if (!markerLayer) return;
  markerLayer.clearLayers();

  items.forEach(item => {
    if (item.lat == null || item.lon == null) return;
    const color   = markerColor(item.bias);
    const popupHTML = `<b>${item.source || ""}</b><br>${(item.text || "").slice(0, 120)}…`;

    L.circleMarker([item.lat, item.lon], {
      radius: 8,
      color,
      fillColor: color,
      fillOpacity: 0.7,
      weight: 1.5,
    })
      .bindPopup(popupHTML)
      .bindTooltip(`${item.source || ""} (${item.bias || "Neutral"})`)
      .addTo(markerLayer);
  });
}

initMap();


/* ═══════════════════════════════════════════════════════════════
   REPORT GENERATION
════════════════════════════════════════════════════════════════ */

/**
 * Requests a situation report from the backend.
 * TODO: Replace mock with:
 *   const res = await fetch(`${API_BASE}${FEED_PORT}/v1/generate_report`);
 *   return res.ok ? (await res.json()).report : null;
 */
async function fetchReport() {
  // --- MOCK ---
  await new Promise(r => setTimeout(r, 1200)); // simulate latency
  return `FLASHPOINT SITREP — ${new Date().toISOString().slice(0,16).replace("T"," ")} UTC

SITUATION OVERVIEW:
Multiple flash-points active across monitored regions.
Narrative divergence detected between Western and Eastern media outlets.

KEY DEVELOPMENTS:
• NATO repositioning observed along eastern flank
• RT/TASS reporting counter-narrative on Kherson operations
• UN emergency session convened — ceasefire proposal tabled
• Satellite imagery confirms troop concentrations near border zones

ASSESSMENT:
Information environment remains highly contested.
Recommend continued monitoring at 2-second intervals.
Cross-reference all single-source reports before escalation.

END OF SITREP`;
  // --- END MOCK ---
}

document.getElementById("generate-report-btn").addEventListener("click", async () => {
  const btn = document.getElementById("generate-report-btn");
  btn.textContent = "⏳ GENERATING SITREP...";
  btn.disabled = true;

  try {
    const report = await fetchReport();
    if (report) {
      latestReport = report;
      const section = document.getElementById("report-section");
      const preview = document.getElementById("report-preview");
      preview.value = report;
      section.classList.remove("hidden");
    } else {
      alert("⚠️ Failed to contact Intelligence Core.");
    }
  } catch (e) {
    alert(`⚠️ Connection Error: ${e.message}`);
  } finally {
    btn.textContent = "GENERATE REPORT";
    btn.disabled = false;
  }
});


/* ─── PDF download ─────────────────────────────────────────── */
document.getElementById("download-pdf-btn").addEventListener("click", () => {
  if (!latestReport) return;

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4" });

  // Header
  doc.setFont("courier", "bold");
  doc.setFontSize(14);
  doc.text("FLASHPOINT INTELLIGENCE SITREP", 105, 15, { align: "center" });

  // Divider
  doc.setDrawColor(0, 229, 255);
  doc.setLineWidth(0.5);
  doc.line(10, 20, 200, 20);

  // Body
  doc.setFont("courier", "normal");
  doc.setFontSize(10);
  const lines = doc.splitTextToSize(latestReport, 185);
  doc.text(lines, 12, 28);

  // Footer
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(148, 163, 184);
    doc.text(`Page ${i} of ${totalPages}`, 105, 290, { align: "center" });
  }

  const timestamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "").replace(" ", "_");
  doc.save(`SITREP_${timestamp}.pdf`);
});


/* ═══════════════════════════════════════════════════════════════
   INTEL CHAT
════════════════════════════════════════════════════════════════ */

/**
 * Sends a query to the intelligence API.
 * TODO: Replace mock with:
 *   const res = await fetch(`${API_BASE}${INTEL_PORT}/v1/query`, {
 *     method: "POST",
 *     headers: { "Content-Type": "application/json" },
 *     body: JSON.stringify({ messages: history }),
 *   });
 *   return res.ok ? await res.json() : "⚠️ Connection Error: Intel Core Unreachable.";
 */
async function sendChatQuery(history) {
  // --- MOCK ---
  await new Promise(r => setTimeout(r, 900));
  const last = history[history.length - 1]?.content || "";
  return `[MOCK INTEL] Query received: "${last}"\n\nAnalysis not yet connected to backend. Backend stub ready at port ${INTEL_PORT}.`;
  // --- END MOCK ---
}

function appendBubble(role, content) {
  const history = document.getElementById("chat-history");
  const bubble  = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = content;
  history.appendChild(bubble);
  history.scrollTop = history.scrollHeight;
  return bubble;
}

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const query = input.value.trim();
  if (!query) return;

  input.value = "";
  input.disabled = true;

  chatMessages.push({ role: "user", content: query });
  appendBubble("user", query);

  const thinkingBubble = appendBubble("thinking", "🔄 Analyzing secure channels...");

  try {
    const response = await sendChatQuery(chatMessages);
    thinkingBubble.remove();
    const content = typeof response === "string" ? response : JSON.stringify(response, null, 2);
    chatMessages.push({ role: "assistant", content });
    appendBubble("assistant", content);
  } catch (err) {
    thinkingBubble.remove();
    appendBubble("assistant", `⚠️ System Error: ${err.message}`);
  } finally {
    input.disabled = false;
    input.focus();
  }
});
