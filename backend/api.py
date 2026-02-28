"""FastAPI Application — Route Definitions Only

Responsibilities:
- Mount the static HTML/CSS/JS frontend at  /
- Ingest the Pathway event stream           POST /v1/stream
- Serve live feed to the dashboard          GET  /v1/frontend/feed
- Trigger SITREP generation                 GET  /v1/generate_report
- Health check                              GET  /health

All business logic lives in dedicated service modules:
  geo_extractor  — spaCy NER + Nominatim geocoding
  report_service — Gemini SITREP generation
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from geo_extractor import extract_location
from report_service import generate_sitrep

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(title="FlashPoint Intel API", version="1.0.0")

# ── In-memory event buffer ────────────────────────────────────────────
# FIFO circular buffer; holds the most recent 100 events from Pathway.
latest_news: deque[Dict[str, Any]] = deque(maxlen=100)

# ── Static frontend ───────────────────────────────────────────────────
# Serve the HTML/CSS/JS dashboard built in frontend/web/.
# Mounted LAST so that /v1/* API routes take priority.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "web"

if _FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_DIR), html=True),
        name="frontend",
    )
else:
    import logging
    logging.getLogger(__name__).warning(
        "Frontend directory not found at %s — static serving disabled.", _FRONTEND_DIR
    )


# ── Routes ────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health():
    """Liveness probe — returns 200 when the API is up."""
    return {"status": "online", "buffer_size": len(latest_news)}


@app.post("/v1/stream", tags=["pipeline"])
async def receive_stream(data: Dict[str, Any]):
    """Ingest a structured event POSTed by the Pathway pipeline.

    Enriches the event with geolocation coordinates (via spaCy NER +
    Nominatim) and stores it in the in-memory circular buffer.

    Args:
        data: Event dict — required keys: source, text, url, timestamp, bias.

    Returns:
        Acknowledgement with current buffer size.
    """
    text = data.get("text", "")

    geo = extract_location(text)
    if geo:
        data["lat"]   = geo["lat"]
        data["lon"]   = geo["lon"]
        data["place"] = geo["place"]

    latest_news.append(data)
    return {"status": "received", "buffer_size": len(latest_news)}


@app.get("/v1/frontend/feed", tags=["frontend"])
def get_feed():
    """Return the current event buffer for dashboard polling.

    Returns:
        List of event dicts (oldest → newest).
    """
    return list(latest_news)


@app.get("/v1/generate_report", tags=["intel"])
def generate_report():
    """Generate and return a Gemini-powered intelligence SITREP.

    Delegates entirely to ``report_service.generate_sitrep``.

    Returns:
        {"report": str} — plain-text SITREP.

    Raises:
        503 if the report service fails (e.g. Gemini API error).
    """
    if not latest_news:
        raise HTTPException(status_code=400, detail="No intelligence data in buffer yet.")

    try:
        report = generate_sitrep(latest_news)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Report generation failed: {exc}") from exc

    return {"report": report}
