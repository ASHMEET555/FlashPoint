"""Real-time tracking service
- Ships: aisstream.io WebSocket (free)
- Flights: OpenSky Network REST API (free, no key needed)
"""

import asyncio
import json
import os
import httpx
import websockets
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

AISSTREAM_KEY = os.getenv("AISSTREAM_API_KEY", "")
OPENSKY_USER  = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASS  = os.getenv("OPENSKY_PASSWORD", "")

# Military callsign prefixes
MILITARY_CALLSIGN_PATTERNS = [
    "RCH",   # US Air Force (Reach)
    "DUKE",  # US Air Force
    "EVAC",  # Medical evacuation
    "RAF",   # Royal Air Force
    "RRR",   # Royal Air Force
    "IAF",   # Israeli Air Force
    "IRGC",  # Iranian Revolutionary Guard
    "IRIS",  # Iranian Air Force
    "RSD",   # Russian Air Force
    "COLT",  # US Army
    "KNIFE", # US Army
    "LOBO",  # US Air Force
    "REACH", # US Air Force
]

EMERGENCY_SQUAWKS = {"7500", "7600", "7700"}

# Oil tanker vessel types (AIS type codes)
OIL_VESSEL_TYPES = {80, 81, 82, 83, 84}  # Tanker types in AIS spec

# In-memory store
_ships: Dict[str, dict] = {}
_flights: Dict[str, dict] = {}


def is_military_flight(callsign: str, squawk: str = "") -> bool:
    if not callsign:
        return False
    cs = callsign.strip().upper()
    if squawk in EMERGENCY_SQUAWKS:
        return True
    return any(cs.startswith(p) for p in MILITARY_CALLSIGN_PATTERNS)


async def stream_ships():
    """Connect to aisstream.io and stream ship positions."""
    if not AISSTREAM_KEY:
        print("⚠️ AISSTREAM_API_KEY not set — ship tracking disabled")
        return

    url = "wss://stream.aisstream.io/v0/stream"
    subscription = {
        "APIKey": AISSTREAM_KEY,
        "BoundingBoxes": [[[-90, -180], [90, 180]]],  # global
        "FilterMessageTypes": ["PositionReport"],
    }

    while True:
        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(subscription))
                print("✅ AIS stream connected")
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        meta = msg.get("MetaData", {})
                        mmsi = str(meta.get("MMSI", ""))
                        if not mmsi:
                            continue

                        vessel_type = meta.get("ShipType", 0)
                        is_tanker = vessel_type in OIL_VESSEL_TYPES

                        _ships[mmsi] = {
                            "mmsi": mmsi,
                            "name": meta.get("ShipName", "Unknown").strip(),
                            "lat": meta.get("latitude"),
                            "lon": meta.get("longitude"),
                            "speed": meta.get("Sog", 0),
                            "heading": meta.get("Cog", 0),
                            "vessel_type": vessel_type,
                            "is_tanker": is_tanker,
                            "timestamp": datetime.now().isoformat(),
                        }
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ AIS stream error: {e} — reconnecting in 10s")
            await asyncio.sleep(10)


async def fetch_flights(region: str = "global") -> List[dict]:
    """Fetch flights from OpenSky Network — free, no key needed."""
    # Bounding boxes for key regions
    REGIONS = {
        "middle_east": (12.0, 25.0, 42.0, 65.0),
        "europe":      (35.0, -25.0, 72.0, 45.0),
        "east_asia":   (10.0, 100.0, 55.0, 145.0),
        "global":      (-90.0, -180.0, 90.0, 180.0),
    }

    lamin, lomin, lamax, lomax = REGIONS.get(region, REGIONS["global"])

    try:
        auth = (OPENSKY_USER, OPENSKY_PASS) if OPENSKY_USER else None
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://opensky-network.org/api/states/all",
                params={"lamin": lamin, "lomin": lomin,
                        "lamax": lamax, "lomax": lomax},
                auth=auth,
            )
            resp.raise_for_status()
            data = resp.json()

        flights = []
        for state in (data.get("states") or []):
            if len(state) < 17:
                continue
            icao24   = state[0] or ""
            callsign = (state[1] or "").strip()
            lat      = state[6]
            lon      = state[5]
            alt      = state[7] or state[13] or 0
            speed    = state[9] or 0
            heading  = state[10] or 0
            squawk   = state[14] or ""
            on_ground = state[8]

            if lat is None or lon is None or on_ground:
                continue

            military = is_military_flight(callsign, squawk)

            flights.append({
                "icao24": icao24,
                "callsign": callsign,
                "lat": lat,
                "lon": lon,
                "altitude": alt,
                "speed": speed,
                "heading": heading,
                "squawk": squawk,
                "military": military,
                "emergency": squawk in EMERGENCY_SQUAWKS,
                "timestamp": datetime.now().isoformat(),
            })

        _flights.clear()
        for f in flights:
            _flights[f["icao24"]] = f

        military_count = sum(1 for f in flights if f["military"])
        print(f"✅ OpenSky: {len(flights)} flights, {military_count} military")
        return flights

    except Exception as e:
        print(f"⚠️ OpenSky error: {e}")
        return list(_flights.values())


def get_ships(tankers_only: bool = False) -> List[dict]:
    ships = list(_ships.values())
    if tankers_only:
        ships = [s for s in ships if s.get("is_tanker")]
    return ships[:500]  # cap at 500 for frontend performance


def get_flights(military_only: bool = False) -> List[dict]:
    flights = list(_flights.values())
    if military_only:
        flights = [f for f in flights if f.get("military")]
    return flights