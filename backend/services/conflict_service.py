"""CFR Global Conflict Tracker Scraper

Scrapes conflict data from Council on Foreign Relations Global Conflict Tracker:
https://www.cfr.org/global-conflict-tracker

Features:
- Scrapes ~30 active conflicts worldwide
- Tracks status (Worsening/Unchanging/Improving)
- Captures impact levels (Critical/Significant/Limited)
- Stores in conflicts.json with 12-hour refresh
- Provides coordinates, regions, and severity scores
"""

import json
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ========== CONFIG ==========
CFR_URL = "https://www.cfr.org/global-conflict-tracker"
CACHE_FILE = Path(__file__).parent.parent / "data" / "conflicts.json"
REFRESH_HOURS = 12

# Region coordinates (approximate centers)
REGION_COORDS = {
    "Europe and Eurasia": {"lat": 50.0, "lng": 20.0},
    "Middle East and North Africa": {"lat": 30.0, "lng": 35.0},
    "Sub-Saharan Africa": {"lat": 0.0, "lng": 20.0},
    "Asia": {"lat": 30.0, "lng": 100.0},
    "Latin America": {"lat": -10.0, "lng": -60.0},
    "North America": {"lat": 45.0, "lng": -100.0}
}

# Conflict-specific coordinates (major flashpoints)
CONFLICT_COORDS = {
    "Ukraine": {"lat": 48.5, "lng": 35.0},
    "Israel": {"lat": 31.5, "lng": 34.8},
    "Gaza": {"lat": 31.5, "lng": 34.5},
    "Syria": {"lat": 35.0, "lng": 38.0},
    "Yemen": {"lat": 15.5, "lng": 44.0},
    "Afghanistan": {"lat": 34.5, "lng": 69.2},
    "Iraq": {"lat": 33.3, "lng": 44.4},
    "Sudan": {"lat": 15.6, "lng": 32.5},
    "Ethiopia": {"lat": 9.0, "lng": 38.7},
    "Somalia": {"lat": 5.2, "lng": 46.2},
    "Myanmar": {"lat": 21.9, "lng": 96.0},
    "Pakistan": {"lat": 30.4, "lng": 69.4},
    "Kashmir": {"lat": 34.1, "lng": 74.8},
    "Taiwan": {"lat": 23.7, "lng": 121.0},
    "South China Sea": {"lat": 12.0, "lng": 115.0},
    "North Korea": {"lat": 39.0, "lng": 127.0},
    "Venezuela": {"lat": 8.0, "lng": -66.0},
    "Colombia": {"lat": 4.6, "lng": -74.1},
    "Mali": {"lat": 17.6, "lng": -4.0},
    "Libya": {"lat": 27.0, "lng": 17.0},
    "Nigeria": {"lat": 9.1, "lng": 7.4},
    "DRC": {"lat": -4.0, "lng": 21.8},
    "Mozambique": {"lat": -18.7, "lng": 35.5},
    "Iran": {"lat": 32.4, "lng": 53.7},
    "Lebanon": {"lat": 33.9, "lng": 35.5},
    "Turkey": {"lat": 39.0, "lng": 35.0}
}


class ConflictService:
    """Manages CFR conflict data scraping and caching."""
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cache from JSON file."""
        if not CACHE_FILE.exists():
            return {"conflicts": [], "metadata": {"last_refresh": None}}
        
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"conflicts": [], "metadata": {"last_refresh": None}}
    
    def _save_cache(self):
        """Persist cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except IOError as e:
            print(f"⚠️ Conflict cache save error: {e}")
    
    def _is_cache_fresh(self) -> bool:
        """Check if cached data is still valid."""
        last_refresh = self.cache["metadata"].get("last_refresh")
        if not last_refresh:
            return False
        
        last_time = datetime.fromisoformat(last_refresh)
        age_hours = (datetime.now() - last_time).total_seconds() / 3600
        return age_hours < REFRESH_HOURS
    
    def _get_coordinates(self, name: str, region: str) -> Dict[str, float]:
        """Get coordinates for conflict by name or region."""
        # Try exact match first
        for key, coords in CONFLICT_COORDS.items():
            if key.lower() in name.lower():
                return coords
        
        # Fallback to region center
        return REGION_COORDS.get(region, {"lat": 0.0, "lng": 0.0})
    
    def _calculate_severity(self, status: str, impact: str) -> int:
        """Calculate severity score 1-10."""
        status_scores = {"Worsening": 3, "Unchanging": 2, "Improving": 1}
        impact_scores = {"Critical": 4, "Significant": 3, "Limited": 2}
        
        base = status_scores.get(status, 2) + impact_scores.get(impact, 2)
        return min(10, base)
    
    async def get_conflicts(self, force_refresh: bool = False) -> Dict:
        """Get conflicts with caching.
        
        Args:
            force_refresh: Force scrape even if cache is fresh
            
        Returns:
            Dict with conflict data and statistics
        """
        if not force_refresh and self._is_cache_fresh():
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "total": len(self.cache["conflicts"]),
                "conflicts": self.cache["conflicts"],
                "statistics": self._calculate_statistics(),
                "cached": True,
                "last_update": self.cache["metadata"]["last_refresh"]
            }
        
        # Scrape fresh data
        return await self._scrape_cfr()
    
    async def _scrape_cfr(self) -> Dict:
        """Scrape CFR website for conflict data."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(CFR_URL)
                response.raise_for_status()
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            conflicts = []
            
            # Find conflict cards/entries
            # CFR structure may vary - this is a generic approach
            conflict_sections = soup.find_all('div', class_=['conflict-item', 'conflict', 'tracker-item'])
            
            if not conflict_sections:
                # Try alternative selectors
                conflict_sections = soup.find_all('article') or soup.find_all('section', class_='conflict')
            
            for idx, section in enumerate(conflict_sections, start=1):
                try:
                    # Extract conflict name
                    title_elem = section.find(['h2', 'h3', 'h4', 'a'])
                    name = title_elem.get_text(strip=True) if title_elem else f"Conflict {idx}"
                    
                    # Extract status
                    status_elem = section.find(class_=['status', 'conflict-status'])
                    status = status_elem.get_text(strip=True) if status_elem else "Unchanging"
                    
                    # Extract impact
                    impact_elem = section.find(class_=['impact', 'severity'])
                    impact = impact_elem.get_text(strip=True) if impact_elem else "Limited"
                    
                    # Extract region
                    region_elem = section.find(class_=['region', 'location'])
                    region = region_elem.get_text(strip=True) if region_elem else "Unknown"
                    
                    # Extract description
                    desc_elem = section.find(['p', 'div'], class_=['description', 'summary'])
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Get coordinates
                    coords = self._get_coordinates(name, region)
                    
                    conflicts.append({
                        "id": idx,
                        "name": name,
                        "region": region,
                        "status": status,
                        "impact_on_us": impact,
                        "coordinates": coords,
                        "severity": self._calculate_severity(status, impact),
                        "description": description[:500] if description else "",
                        "last_update": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"⚠️ Error parsing conflict {idx}: {e}")
                    continue
            
            # Update cache
            self.cache["conflicts"] = conflicts
            self.cache["metadata"]["last_refresh"] = datetime.now().isoformat()
            self._save_cache()
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "total": len(conflicts),
                "conflicts": conflicts,
                "statistics": self._calculate_statistics(),
                "cached": False
            }
            
        except Exception as e:
            print(f"⚠️ CFR scrape error: {e}")
            # Return cached data if available
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "total": len(self.cache["conflicts"]),
                "conflicts": self.cache["conflicts"],
                "statistics": self._calculate_statistics(),
                "cached": True
            }
    
    def _calculate_statistics(self) -> Dict:
        """Calculate conflict statistics."""
        conflicts = self.cache["conflicts"]
        
        by_status = {}
        by_impact = {}
        by_region = {}
        
        for conflict in conflicts:
            status = conflict.get("status", "Unknown")
            impact = conflict.get("impact_on_us", "Unknown")
            region = conflict.get("region", "Unknown")
            
            by_status[status] = by_status.get(status, 0) + 1
            by_impact[impact] = by_impact.get(impact, 0) + 1
            by_region[region] = by_region.get(region, 0) + 1
        
        return {
            "by_status": by_status,
            "by_impact": by_impact,
            "by_region": by_region
        }
    
    def get_conflict_by_id(self, conflict_id: int) -> Optional[Dict]:
        """Get single conflict by ID."""
        for conflict in self.cache["conflicts"]:
            if conflict.get("id") == conflict_id:
                return conflict
        return None


# Singleton instance
_conflict_service = None

def get_conflict_service() -> ConflictService:
    """Get or create ConflictService singleton."""
    global _conflict_service
    if _conflict_service is None:
        _conflict_service = ConflictService()
    return _conflict_service
