import { updateClock } from './js/utils.js';
import { initFeed } from './js/feed.js';
import { initMap } from './js/map.js';
import { initChat } from './js/chat.js';
import { initCommodities } from './js/commodities.js';
import { initConflicts } from './js/conflicts.js';
import { initReports } from './js/reports.js';

function init() {
    console.log("Initializing FlashPoint...");
    updateClock();
    setInterval(updateClock, 1000);
    initMap();
    initFeed();
    initChat();
    initCommodities();
    initConflicts();
    initReports();
    console.log("FlashPoint operational");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
