/**
 * map.js - Leaflet map with hotspots and conflict markers
 */

import { escapeHTML } from './utils.js';

export let map, markerLayer;
const locationFreq = {};
const HOTSPOT_COLORS = {
    1: "#00FF00",
    5: "#FFFF00",
    10: "#FF8800",
    20: "#FF0000"
};

/**
 * Initialize Leaflet map
 */
export function initMap() {
    map = L.map("map", {
        center: [30, 20],
        zoom: 2,
        zoomControl: true,
        scrollWheelZoom: true
    });

    // Dark tile layer
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    markerLayer = L.layerGroup().addTo(map);
    
    console.log("🗺️  Map initialized");
}

/**
 * Get hotspot color based on frequency
 */
function getHotspotColor(count) {
    if (count >= 20) return HOTSPOT_COLORS[20];
    if (count >= 10) return HOTSPOT_COLORS[10];
    if (count >= 5) return HOTSPOT_COLORS[5];
    return HOTSPOT_COLORS[1];
}

/**
 * Update map hotspot for an event
 */
export function updateMapHotspot(item) {
    if (!item.lat || !item.lon) return;

    const place = item.place || "Unknown";
    const key = `${place}|${item.lat.toFixed(2)}|${item.lon.toFixed(2)}`;

    locationFreq[key] = (locationFreq[key] || 0) + 1;
    const count = locationFreq[key];

    // Remove old marker
    markerLayer.eachLayer(layer => {
        if (layer.options.locationKey === key) {
            markerLayer.removeLayer(layer);
        }
    });

    // Add new circle with updated radius
    const radius = Math.sqrt(count) * 50000; // Scale radius
    const color = getHotspotColor(count);

    const circle = L.circle([item.lat, item.lon], {
        color: color,
        fillColor: color,
        fillOpacity: 0.4,
        radius: radius,
        locationKey: key
    }).addTo(markerLayer);

    circle.bindPopup(`
        <strong>${escapeHTML(place)}</strong><br>
        Events: ${count}<br>
        Latest: ${escapeHTML(item.text.substring(0, 100))}...
    `);
}

/**
 * Render conflict markers from API
 */
export async function renderConflictMarkers(conflicts) {
    if (!conflicts || !Array.isArray(conflicts)) return;

    conflicts.forEach(conflict => {
        if (!conflict.lat || !conflict.lon) return;

        const severityColors = {
            critical: "#FF0000",
            high: "#FF8800",
            medium: "#FFFF00",
            low: "#00FF00"
        };

        const color = severityColors[conflict.severity?.toLowerCase()] || "#FFFFFF";
        const radius = 30000; // Fixed size for conflicts

        const circle = L.circle([conflict.lat, conflict.lon], {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            radius: radius,
            weight: 2
        }).addTo(markerLayer);

        circle.bindPopup(`
            <strong>${escapeHTML(conflict.name)}</strong><br>
            <em>${escapeHTML(conflict.status || "Active")}</em><br>
            Severity: ${escapeHTML(conflict.severity || "Unknown")}<br>
            ${conflict.description ? escapeHTML(conflict.description.substring(0, 150)) + "..." : ""}
        `);
    });

    console.log(`✅ Rendered ${conflicts.length} conflict markers`);
}
