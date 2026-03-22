"""CFR Global Conflict Tracker — with fallback seed data

Since CFR uses JS rendering, we use a curated seed list
enriched periodically from Wikipedia current events RSS.
Cache: root data/conflicts.json, refreshed every 12 hours.
"""

import json
import feedparser
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "conflicts.json"
REFRESH_HOURS = 12

FALLBACK_CONFLICTS = [
    {"id": 1,  "name": "Russia-Ukraine War",       "region": "Europe",       "status": "Worsening",   "impact_on_us": "Critical",    "severity": 9, "coordinates": {"lat": 48.5,  "lng": 35.0},  "description": "Full-scale Russian invasion of Ukraine ongoing since February 2022."},
    {"id": 2,  "name": "Israel-Hamas War",          "region": "Middle East",  "status": "Worsening",   "impact_on_us": "Critical",    "severity": 9, "coordinates": {"lat": 31.5,  "lng": 34.5},  "description": "Conflict in Gaza following October 7 2023 attacks."},
    {"id": 3,  "name": "Sudan Civil War",           "region": "Africa",       "status": "Worsening",   "impact_on_us": "Significant", "severity": 8, "coordinates": {"lat": 15.6,  "lng": 32.5},  "description": "RSF vs SAF conflict causing major humanitarian crisis in Darfur."},
    {"id": 4,  "name": "Yemen Conflict",            "region": "Middle East",  "status": "Unchanging",  "impact_on_us": "Significant", "severity": 7, "coordinates": {"lat": 15.5,  "lng": 44.0},  "description": "Houthi attacks on Red Sea shipping continuing."},
    {"id": 5,  "name": "Myanmar Civil War",         "region": "Asia",         "status": "Worsening",   "impact_on_us": "Limited",     "severity": 7, "coordinates": {"lat": 21.9,  "lng": 96.0},  "description": "Military junta fighting resistance coalition forces."},
    {"id": 6,  "name": "Taiwan Strait Tensions",    "region": "Asia",         "status": "Unchanging",  "impact_on_us": "Critical",    "severity": 7, "coordinates": {"lat": 23.7,  "lng": 121.0}, "description": "PLA military exercises near Taiwan continuing."},
    {"id": 7,  "name": "Iran Nuclear Standoff",     "region": "Middle East",  "status": "Worsening",   "impact_on_us": "Critical",    "severity": 8, "coordinates": {"lat": 32.4,  "lng": 53.7},  "description": "Iran enrichment at 60%, IAEA access restricted."},
    {"id": 8,  "name": "Sahel Insurgency",          "region": "Africa",       "status": "Worsening",   "impact_on_us": "Limited",     "severity": 6, "coordinates": {"lat": 14.0,  "lng": 2.0},   "description": "Jihadist insurgency across Mali, Burkina Faso, Niger."},
    {"id": 9,  "name": "North Korea Provocations",  "region": "Asia",         "status": "Worsening",   "impact_on_us": "Critical",    "severity": 7, "coordinates": {"lat": 39.0,  "lng": 127.0}, "description": "Ballistic missile tests and nuclear program expansion."},
    {"id": 10, "name": "DRC Conflict",              "region": "Africa",       "status": "Worsening",   "impact_on_us": "Limited",     "severity": 7, "coordinates": {"lat": -4.0,  "lng": 21.8},  "description": "M23 advances in eastern DRC backed by Rwanda."},
    {"id": 11, "name": "Ethiopia-Tigray",           "region": "Africa",       "status": "Unchanging",  "impact_on_us": "Limited",     "severity": 5, "coordinates": {"lat": 14.0,  "lng": 38.5},  "description": "Fragile ceasefire holds but tensions remain high."},
    {"id": 12, "name": "South China Sea Tensions",  "region": "Asia",         "status": "Unchanging",  "impact_on_us": "Critical",    "severity": 6, "coordinates": {"lat": 12.0,  "lng": 115.0}, "description": "China vs Philippines standoffs at disputed reefs."},
    {"id": 13, "name": "Lebanon Instability",       "region": "Middle East",  "status": "Worsening",   "impact_on_us": "Significant", "severity": 6, "coordinates": {"lat": 33.9,  "lng": 35.5},  "description": "Post-war reconstruction stalled, Hezbollah weakened."},
    {"id": 14, "name": "Haiti Gang Crisis",         "region": "Americas",     "status": "Worsening",   "impact_on_us": "Significant", "severity": 7, "coordinates": {"lat": 18.9,  "lng": -72.3}, "description": "Gang coalitions control most of Port-au-Prince."},
    {"id": 15, "name": "Venezuela Crisis",          "region": "Americas",     "status": "Unchanging",  "impact_on_us": "Significant", "severity": 5, "coordinates": {"lat": 8.0,   "lng": -66.0}, "description": "Political and economic crisis with mass migration continuing."},
]


class ConflictService:

    def __init__(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    data = json.load(f)
                    if data.get("conflicts"):
                        return data
            except Exception:
                pass
        return {"conflicts": [], "metadata": {"last_refresh": None}}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Conflict cache save error: {e}")

    def _is_fresh(self) -> bool:
        last = self.cache["metadata"].get("last_refresh")
        if not last:
            return False
        age = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600
        return age < REFRESH_HOURS

    def _calculate_statistics(self) -> Dict:
        conflicts = self.cache["conflicts"]
        by_status, by_impact, by_region = {}, {}, {}
        for c in conflicts:
            s = c.get("status", "Unknown")
            i = c.get("impact_on_us", "Unknown")
            r = c.get("region", "Unknown")
            by_status[s] = by_status.get(s, 0) + 1
            by_impact[i] = by_impact.get(i, 0) + 1
            by_region[r] = by_region.get(r, 0) + 1
        return {"by_status": by_status, "by_impact": by_impact, "by_region": by_region}

    async def get_conflicts(self, force_refresh: bool = False) -> Dict:
        # Always seed with fallback if cache is empty
        if not self.cache["conflicts"]:
            self.cache["conflicts"] = list(FALLBACK_CONFLICTS)
            self.cache["metadata"]["last_refresh"] = datetime.now().isoformat()
            self._save_cache()

        if not force_refresh and self._is_fresh():
            return {
                "success": True,
                "conflicts": self.cache["conflicts"],
                "total": len(self.cache["conflicts"]),
                "statistics": self._calculate_statistics(),
                "cached": True,
                "last_update": self.cache["metadata"]["last_refresh"],
            }

        # Try to enrich with Wikipedia current events RSS
        conflicts = list(FALLBACK_CONFLICTS)
        try:
            feed = feedparser.parse(
                "https://en.wikinews.org/w/index.php?title=Special:NewPages&feed=rss"
            )
            next_id = len(FALLBACK_CONFLICTS) + 1
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:300]
                if any(kw in (title + summary).lower() for kw in
                       ["war", "conflict", "attack", "missile", "troops",
                        "strike", "crisis", "killed", "offensive"]):
                    conflicts.append({
                        "id": next_id,
                        "name": title[:80],
                        "region": "Global",
                        "status": "Worsening",
                        "impact_on_us": "Significant",
                        "severity": 6,
                        "coordinates": {"lat": 0.0, "lng": 0.0},
                        "description": summary,
                        "last_update": datetime.now().isoformat(),
                    })
                    next_id += 1
            print(f"✅ Conflicts: enriched with {len(conflicts) - len(FALLBACK_CONFLICTS)} Wikinews items")
        except Exception as e:
            print(f"⚠️ Wikinews RSS failed: {e} — using fallback only")

        self.cache["conflicts"] = conflicts
        self.cache["metadata"]["last_refresh"] = datetime.now().isoformat()
        self._save_cache()

        return {
            "success": True,
            "conflicts": conflicts,
            "total": len(conflicts),
            "statistics": self._calculate_statistics(),
            "cached": False,
            "last_update": self.cache["metadata"]["last_refresh"],
        }

    def get_conflict_by_id(self, conflict_id: int) -> Optional[Dict]:
        for c in self.cache["conflicts"]:
            if c.get("id") == conflict_id:
                return c
        return None


_conflict_service = None

def get_conflict_service() -> ConflictService:
    global _conflict_service
    if _conflict_service is None:
        _conflict_service = ConflictService()
    return _conflict_service