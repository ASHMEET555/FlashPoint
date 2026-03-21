"""Commodity Price Service

Uses two genuinely free APIs:
- gold-api.com      — Gold (XAU) and Silver (XAG), no credit card
- oilpriceapi.com   — WTI and Brent crude, free tier

Cache: data/commodity_cache.json, refreshed every 3 hours.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

OIL_API_KEY  = os.getenv("OIL_API_KEY", "")

# Cache lives in the root data/ folder
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "commodity_cache.json"
CACHE_DURATION_HOURS = 3

COMMODITIES = {
    "XAU":          {"name": "Gold",           "unit": "troy oz",  "source": "gold"},
    "XAG":          {"name": "Silver",          "unit": "troy oz",  "source": "gold"},
    "WTI_USD":      {"name": "WTI Crude Oil",   "unit": "barrel",   "source": "oil"},
    "BRENT_USD":    {"name": "Brent Crude Oil", "unit": "barrel",   "source": "oil"},
}


class CommodityService:

    def __init__(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"prices": {}, "last_refresh": None}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Cache save error: {e}")

    def _is_fresh(self) -> bool:
        last = self.cache.get("last_refresh")
        if not last:
            return False
        age = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600
        return age < CACHE_DURATION_HOURS

    async def _fetch_gold(self) -> Dict[str, float]:
        """Fetch XAU and XAG from gold-api.com — no key required"""
        prices = {}
        for symbol in ["XAU", "XAG"]:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://api.gold-api.com/price/{symbol}"
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    prices[symbol] = float(data["price"])
                    print(f"✅ {symbol}: ${prices[symbol]:.2f}")
            except Exception as e:
                print(f"⚠️ Gold API error for {symbol}: {e}")
        return prices

    async def _fetch_oil(self) -> Dict[str, float]:
        """Fetch WTI and Brent from oilpriceapi.com"""
        prices = {}
        if not OIL_API_KEY:
            print("⚠️ OIL_API_KEY not set — skipping oil fetch")
            return prices

        for code in ["WTI_USD", "BRENT_USD"]:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://api.oilpriceapi.com/v1/prices/latest",
                        params={"by_code": code},
                        headers={
                            "Authorization": f"Token {OIL_API_KEY}",
                            "Content-Type": "application/json"
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    prices[code] = float(data["data"]["price"])
                    print(f"✅ {code}: ${prices[code]:.2f}")
            except Exception as e:
                print(f"⚠️ Oil API error for {code}: {e}")

        return prices

    async def fetch_prices(self, symbols: Optional[List[str]] = None) -> Dict:
        """Fetch prices with caching. Returns cached data if fresh."""
        if self._is_fresh() and self.cache["prices"]:
            return self._format_response(cached=True)

        # Fetch fresh data
        gold_prices = await self._fetch_gold()
        oil_prices  = await self._fetch_oil()
        all_prices  = {**gold_prices, **oil_prices}

        if all_prices:
            timestamp = datetime.now().isoformat()
            for symbol, price in all_prices.items():
                self.cache["prices"][symbol] = {
                    "rate": price,
                    "timestamp": timestamp,
                    "unit": COMMODITIES.get(symbol, {}).get("unit", "USD"),
                    "name": COMMODITIES.get(symbol, {}).get("name", symbol),
                }
            self.cache["last_refresh"] = timestamp
            self._save_cache()

        return self._format_response(cached=False)

    def _format_response(self, cached: bool) -> Dict:
        prices = self.cache.get("prices", {})
        formatted = {}
        for symbol, data in prices.items():
            if data:
                formatted[symbol] = {
                    "rate": data.get("rate", 0),
                    "name": data.get("name", COMMODITIES.get(symbol, {}).get("name", symbol)),
                    "unit": data.get("unit", "USD"),
                    "cached_at": data.get("timestamp"),
                }
        return {
            "success": bool(formatted),
            "timestamp": datetime.now().isoformat(),
            "data": formatted,
            "prices": formatted,   # keep both keys for frontend compatibility
            "cached": cached,
            "last_refresh": self.cache.get("last_refresh"),
        }


_service = None

def get_commodity_service() -> CommodityService:
    global _service
    if _service is None:
        _service = CommodityService()
    return _service