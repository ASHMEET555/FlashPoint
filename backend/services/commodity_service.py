"""Commodity Price Monitoring Service

Fetches real-time commodity prices (Gold, Silver, Oil) from CommodityAPI
with intelligent caching and quota management.

Features:
- 3-hour cache with automatic refresh
- Alternate between two API keys for load balancing
- Track API usage against 2000 calls/year limit per key
- Fallback to cached data if API fails
- Persistent storage in commodity_cache.json
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

# ========== CONFIG ==========
API_KEY_1 = os.getenv("COMMODITY_PRICE_API1")
API_KEY_2 = os.getenv("COMMODITY_PRICE_API2", "")  # Optional second key

BASE_URL = "https://api.commodityapi.com/api/latest"
CACHE_FILE = Path(__file__).parent.parent / "data" / "commodity_cache.json"
CACHE_DURATION_HOURS = 3
YEARLY_QUOTA_PER_KEY = 2000

# Commodity symbols to track
SYMBOLS = {
    "XAU": {"name": "Gold", "unit": "troy oz", "icon": "🥇"},
    "XAG": {"name": "Silver", "unit": "troy oz", "icon": "🥈"},
    "WTIOIL-FUT": {"name": "WTI Crude Oil", "unit": "barrel", "icon": "🛢️"},
    "BRENTOIL-FUT": {"name": "Brent Crude Oil", "unit": "barrel", "icon": "🛢️"}
}


class CommodityService:
    """Manages commodity price fetching with caching and quota tracking."""
    
    def __init__(self):
        self.cache = self._load_cache()
        self.api_keys = [k for k in [API_KEY_1, API_KEY_2] if k]
        if not self.api_keys:
            raise ValueError("At least one COMMODITY_PRICE_API key must be set in .env")
    
    def _load_cache(self) -> Dict:
        """Load cache from JSON file."""
        if not CACHE_FILE.exists():
            return self._initialize_cache()
        
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Cache load error: {e}, reinitializing")
            return self._initialize_cache()
    
    def _initialize_cache(self) -> Dict:
        """Create fresh cache structure."""
        return {
            "prices": {},
            "metadata": {
                "last_refresh": None,
                "api_keys": {
                    key: {"calls_used": 0, "quota": YEARLY_QUOTA_PER_KEY, "last_reset": datetime.now().year}
                    for key in self.api_keys
                }
            }
        }
    
    def _save_cache(self):
        """Persist cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except IOError as e:
            print(f"⚠️ Cache save error: {e}")
    
    def _is_cache_fresh(self) -> bool:
        """Check if cached data is still valid."""
        last_refresh = self.cache["metadata"].get("last_refresh")
        if not last_refresh:
            return False
        
        last_time = datetime.fromisoformat(last_refresh)
        age_hours = (datetime.now() - last_time).total_seconds() / 3600
        return age_hours < CACHE_DURATION_HOURS
    
    def _select_api_key(self) -> Optional[str]:
        """Select API key with lowest usage."""
        current_year = datetime.now().year
        keys_metadata = self.cache["metadata"]["api_keys"]
        
        # Reset counters if new year
        for key_data in keys_metadata.values():
            if key_data.get("last_reset", current_year) < current_year:
                key_data["calls_used"] = 0
                key_data["last_reset"] = current_year
        
        # Find key with most remaining quota
        available_keys = [
            (key, data["quota"] - data["calls_used"])
            for key, data in keys_metadata.items()
            if data["calls_used"] < data["quota"]
        ]
        
        if not available_keys:
            print("⚠️ All API keys exhausted quota!")
            return None
        
        return max(available_keys, key=lambda x: x[1])[0]
    
    async def fetch_prices(self, symbols: Optional[List[str]] = None) -> Dict:
        """Fetch commodity prices with caching.
        
        Args:
            symbols: List of commodity symbols (defaults to all tracked symbols)
            
        Returns:
            Dict with price data and metadata
        """
        if symbols is None:
            symbols = list(SYMBOLS.keys())
        
        # Return cached data if fresh
        if self._is_cache_fresh():
            cached_prices = {
                sym: self.cache["prices"].get(sym)
                for sym in symbols
                if sym in self.cache["prices"]
            }
            if all(cached_prices.values()):
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "data": cached_prices,
                    "cached": True,
                    "api_usage": self._get_usage_stats()
                }
        
        # Fetch fresh data
        return await self._fetch_from_api(symbols)
    
    async def _fetch_from_api(self, symbols: List[str]) -> Dict:
        """Fetch data from CommodityAPI."""
        api_key = self._select_api_key()
        if not api_key:
            # Fallback to cache if available
            return {
                "success": False,
                "error": "API quota exhausted",
                "data": {sym: self.cache["prices"].get(sym) for sym in symbols},
                "cached": True,
                "api_usage": self._get_usage_stats()
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    BASE_URL,
                    params={
                        "access_key": api_key,
                        "base": "USD",
                        "symbols": ",".join(symbols)
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            if not data.get("success"):
                raise Exception(data.get("error", {}).get("info", "API returned error"))
            
            # Update cache
            self._update_cache(data["data"]["rates"], api_key)
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    sym: {
                        "rate": self.cache["prices"][sym]["rate"],
                        "unit": SYMBOLS[sym]["unit"],
                        "quote": "USD",
                        "cached": False,
                        "cached_at": self.cache["prices"][sym]["timestamp"]
                    }
                    for sym in symbols
                    if sym in self.cache["prices"]
                },
                "cached": False,
                "api_usage": self._get_usage_stats()
            }
            
        except (httpx.HTTPError, Exception) as e:
            print(f"⚠️ API fetch error: {e}")
            # Fallback to cache
            return {
                "success": False,
                "error": str(e),
                "data": {
                    sym: self.cache["prices"].get(sym)
                    for sym in symbols
                    if sym in self.cache["prices"]
                },
                "cached": True,
                "api_usage": self._get_usage_stats()
            }
    
    def _update_cache(self, rates: Dict[str, float], api_key: str):
        """Update cache with fresh data."""
        timestamp = datetime.now().isoformat()
        
        for symbol, rate in rates.items():
            self.cache["prices"][symbol] = {
                "rate": rate,
                "timestamp": timestamp,
                "unit": SYMBOLS.get(symbol, {}).get("unit", "unknown")
            }
        
        self.cache["metadata"]["last_refresh"] = timestamp
        self.cache["metadata"]["api_keys"][api_key]["calls_used"] += 1
        self._save_cache()
    
    def _get_usage_stats(self) -> Dict:
        """Get API usage statistics."""
        stats = self.cache["metadata"]["api_keys"]
        total_used = sum(data["calls_used"] for data in stats.values())
        total_quota = sum(data["quota"] for data in stats.values())
        
        return {
            "used": total_used,
            "quota": total_quota,
            "remaining": total_quota - total_used,
            "keys": len(stats),
            "expires": f"{datetime.now().year}-12-31"
        }
    
    def get_price_sync(self, symbol: str) -> Optional[Dict]:
        """Get single price synchronously from cache."""
        return self.cache["prices"].get(symbol)


# Singleton instance
_service = None

def get_commodity_service() -> CommodityService:
    """Get or create CommodityService singleton."""
    global _service
    if _service is None:
        _service = CommodityService()
    return _service
