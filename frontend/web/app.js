import { updateClock } from './js/utils.js?v=3';
import { initFeed } from './js/feed.js?v=3';
import { initMap } from './js/map.js?v=3';
import { initChat } from './js/chat.js?v=3';
import { initCommodities } from './js/commodities.js?v=3';
import { initConflicts } from './js/conflicts.js?v=3';
import { initReports } from './js/reports.js?v=3';

function init() {
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
