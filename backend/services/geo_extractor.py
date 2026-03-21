"""Geopolitical Entity Extractor

Uses spaCy's named-entity recognition (NER) to identify geopolitical
entities (GPE) and locations (LOC) in free text, then resolves them
to geographic coordinates for map visualisation.

Resolution strategy (two-tier):
1. **Coordinate cache** — an in-process dict covering ~50 high-frequency
   geopolitical hotspots for zero-latency, zero-network lookups.
2. **Nominatim fallback** — for any entity not in the cache, a single
   HTTP request to the OSM Nominatim geocoding API is made and its
   result is cached for the lifetime of the process.

Public API
----------
    extract_location(text: str) -> dict | None
        Returns {"lat": float, "lon": float, "place": str} for the
        first resolvable GPE/LOC entity found in *text*, or None.

    extract_all_locations(text: str) -> list[dict]
        Returns one entry per unique resolvable entity in *text*.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import requests
import spacy

logger = logging.getLogger(__name__)

# ── spaCy model ───────────────────────────────────────────────────────
# Load once at import time; en_core_web_sm is ~12 MB and ships NER.
# Run:  python -m spacy download en_core_web_sm
try:
    _nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning(
        "spaCy model 'en_core_web_sm' not found. "
        "Run: python -m spacy download en_core_web_sm"
    )
    _nlp = None


# ── Coordinate cache ──────────────────────────────────────────────────
# Covers the most common geopolitical hotspots to avoid network calls.
# Keys are title-cased place names; values are (lat, lon) tuples.
_COORD_CACHE: dict[str, tuple[float, float]] = {
    # Eastern Europe / former Soviet
    "Ukraine":        (48.3794,  31.1656),
    "Kyiv":           (50.4501,  30.5234),
    "Kharkiv":        (49.9935,  36.2304),
    "Mariupol":       (47.0951,  37.5494),
    "Kherson":        (46.6354,  32.6169),
    "Zaporizhzhia":   (47.8388,  35.1396),
    "Donbas":         (48.0159,  38.1859),
    "Crimea":         (45.3469,  34.0269),
    "Russia":         (61.5240, 105.3188),
    "Moscow":         (55.7558,  37.6173),
    "St. Petersburg": (59.9343,  30.3351),
    "Belarus":        (53.7098,  27.9534),
    "Minsk":          (53.9045,  27.5615),
    "Moldova":        (47.4116,  28.3699),
    # Middle East
    "Israel":         (31.0461,  34.8516),
    "Gaza":           (31.5000,  34.4660),
    "West Bank":      (31.9522,  35.2332),
    "Lebanon":        (33.8547,  35.8623),
    "Beirut":         (33.8886,  35.4955),
    "Syria":          (34.8021,  38.9968),
    "Damascus":       (33.5138,  36.2765),
    "Iran":           (32.4279,  53.6880),
    "Tehran":         (35.6892,  51.3890),
    "Iraq":           (33.2232,  43.6793),
    "Baghdad":        (33.3406,  44.4009),
    "Yemen":          (15.5527,  48.5164),
    "Saudi Arabia":   (23.8859,  45.0792),
    "Turkey":         (38.9637,  35.2433),
    "Ankara":         (39.9334,  32.8597),
    # Asia-Pacific
    "China":          (35.8617, 104.1954),
    "Beijing":        (39.9042, 116.4074),
    "Taiwan":         (23.6978, 120.9605),
    "Taipei":         (25.0330, 121.5654),
    "Hong Kong":      (22.3193, 114.1694),
    "North Korea":    (40.3399, 127.5101),
    "South Korea":    (35.9078, 127.7669),
    "Japan":          (36.2048, 138.2529),
    "Tokyo":          (35.6762, 139.6503),
    "India":          (20.5937,  78.9629),
    "Delhi":          (28.6139,  77.2090),
    "Pakistan":       (30.3753,  69.3451),
    "Afghanistan":    (33.9391,  67.7100),
    # Americas
    "USA":            (37.0902, -95.7129),
    "Washington":     (38.9072, -77.0369),
    "New York":       (40.7128, -74.0060),
    "Canada":         (56.1304, -106.3468),
    "Mexico":         (23.6345, -102.5528),
    "Venezuela":      ( 6.4238, -66.5897),
    # Africa
    "Sudan":          (12.8628,  30.2176),
    "Ethiopia":       ( 9.1450,  40.4897),
    "Somalia":        ( 5.1521,  46.1996),
    "Libya":          (26.3351,  17.2283),
    # Europe
    "United Kingdom": (55.3781,  -3.4360),
    "London":         (51.5074,  -0.1278),
    "Germany":        (51.1657,  10.4515),
    "France":         (46.2276,   2.2137),
    "NATO":           (50.8503,   4.3517),  # Brussels (HQ)
    "EU":             (50.8503,   4.3517),
    "United Nations": (40.7489, -73.9680),  # UN HQ New York
}


@lru_cache(maxsize=512)
def _nominatim_lookup(place: str) -> Optional[tuple[float, float]]:
    """Query OSM Nominatim for coordinates of *place*.

    Results are cached via ``lru_cache`` for the process lifetime.
    Returns (lat, lon) on success, None on failure.
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "FlashPoint-IntelEngine/1.0"},
            timeout=3,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        logger.debug("Nominatim lookup failed for %r: %s", place, exc)
    return None


def _resolve(place: str) -> Optional[dict]:
    """Resolve a place name to a coordinate dict.

    Checks the in-process cache first; falls back to Nominatim.

    Returns:
        {"lat": float, "lon": float, "place": str} or None.
    """
    key = place.strip().title()

    # Tier 1: in-process cache
    if key in _COORD_CACHE:
        lat, lon = _COORD_CACHE[key]
        return {"lat": lat, "lon": lon, "place": key}

    # Tier 2: Nominatim (result auto-cached by lru_cache)
    coords = _nominatim_lookup(key)
    if coords:
        lat, lon = coords
        _COORD_CACHE[key] = (lat, lon)   # populate cache for next hit
        return {"lat": lat, "lon": lon, "place": key}

    return None


# ── Public API ────────────────────────────────────────────────────────

def extract_location(text: str) -> Optional[dict]:
    """Return coordinates for the first resolvable geopolitical entity in *text*.

    Uses spaCy NER (GPE + LOC labels) when available; falls back to a
    simple title-case scan of the coordinate cache if the model is absent.

    Args:
        text: Raw event text.

    Returns:
        {"lat": float, "lon": float, "place": str} or None.
    """
    if not text:
        return None

    candidates: list[str] = []

    if _nlp is not None:
        doc = _nlp(text[:1000])   # cap at 1 000 chars for speed
        candidates = [
            ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC")
        ]
    else:
        # Graceful degradation: scan cache keys directly
        candidates = [k for k in _COORD_CACHE if k in text]

    for candidate in candidates:
        result = _resolve(candidate)
        if result:
            return result

    return None


def extract_all_locations(text: str) -> list[dict]:
    """Return one coordinate dict per unique resolvable entity in *text*.

    Useful for mapping multiple hotspots mentioned in a single article.

    Args:
        text: Raw event text.

    Returns:
        List of {"lat": float, "lon": float, "place": str} dicts.
    """
    if not text:
        return []

    candidates: list[str] = []

    if _nlp is not None:
        doc = _nlp(text[:1000])
        seen: set[str] = set()
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC") and ent.text not in seen:
                candidates.append(ent.text)
                seen.add(ent.text)
    else:
        candidates = [k for k in _COORD_CACHE if k in text]

    results = []
    for candidate in candidates:
        resolved = _resolve(candidate)
        if resolved:
            results.append(resolved)

    return results
