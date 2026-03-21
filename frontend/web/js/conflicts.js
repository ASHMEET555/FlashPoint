/**
 * conflicts.js - Global conflict tracker integration
 */

import { API_BASE, ENDPOINTS } from './utils.js';
import { renderConflictMarkers } from './map.js';

/**
 * Fetch and render conflicts
 */
async function fetchConflicts() {
    try {
        const resp = await fetch(`${API_BASE}${ENDPOINTS.conflicts}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        if (data.success && data.conflicts) {
            renderConflictMarkers(data.conflicts);
            console.log(`✅ Loaded ${data.conflicts.length} conflicts`);
        }

    } catch (err) {
        console.error("Failed to fetch conflicts:", err);
    }
}

/**
 * Initialize conflicts module
 */
export function initConflicts() {
    fetchConflicts();
    
    // Refresh every 12 hours
    setInterval(fetchConflicts, 12 * 60 * 60 * 1000);
    
    console.log("⚔️  Conflicts tracker initialized");
}
