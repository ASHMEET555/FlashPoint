"""FastAPI Application — Route Definitions Only

Responsibilities:
- Mount the static HTML/CSS/JS frontend at  /
- Ingest the Pathway event stream           POST /v1/stream
- Push new events to browsers               GET  /v1/feed/stream  (SSE)
- Serve live feed snapshot                  GET  /v1/frontend/feed
- Trigger SITREP generation                 GET  /v1/generate_report
- SSE-streaming LLM chat                    POST /v1/chat
- Health check                              GET  /health

All business logic lives in dedicated service modules:
  geo_extractor  — spaCy NER + Nominatim geocoding
  report_service — Gemini SITREP generation
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from geo_extractor import extract_location
from report_service import generate_pdf_bytes, generate_sitrep

logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(title="FlashPoint Intel API", version="1.0.0")

# Allow the frontend (any origin during dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory event buffer ────────────────────────────────────────────
# Circular buffer — last 100 events from Pathway.
latest_news: deque[Dict[str, Any]] = deque(maxlen=100)

# SSE subscriber queues — one asyncio.Queue per connected browser tab.
_sse_subscribers: List[asyncio.Queue] = []


def _broadcast(event: Dict[str, Any]) -> None:
    """Push a new event to every active SSE subscriber queue."""
    dead = []
    for q in _sse_subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _sse_subscribers.remove(q)


# ── Static frontend ───────────────────────────────────────────────────
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "web"
_ASSETS_DIR   = Path(__file__).resolve().parent.parent / "frontend" / "assets"
_THEMES_DIR   = Path(__file__).resolve().parent.parent / "frontend" / "themes"


# ── Routes ────────────────────────────────────────────────────────────

@app.get("/theme-preview", tags=["meta"], include_in_schema=False)
def theme_preview():
    """Serve the interactive theme-picker preview page."""
    return FileResponse(str(_THEMES_DIR / "preview.html"), media_type="text/html")

@app.get("/health", tags=["meta"])
def health():
    """Liveness probe."""
    return {"status": "online", "buffer_size": len(latest_news)}


@app.post("/v1/stream", tags=["pipeline"])
async def receive_stream(data: Dict[str, Any]):
    """Ingest a structured event POSTed by the Pathway pipeline.

    Enriches with geolocation, stores in buffer, and broadcasts to all
    active SSE subscribers so the browser updates instantly.
    """
    text = data.get("text", "")

    geo = extract_location(text)
    if geo:
        data.setdefault("lat",   geo["lat"])
        data.setdefault("lon",   geo["lon"])
        data.setdefault("place", geo["place"])

    latest_news.append(data)
    _broadcast(data)
    return {"status": "received", "buffer_size": len(latest_news)}


async def _sse_generator(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted messages from the subscriber queue forever."""
    # Send current buffer as a snapshot on connect
    for item in latest_news:
        yield f"data: {json.dumps(item)}\n\n"

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=25)
            yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            # Keep-alive comment so proxies/browsers don't drop the connection
            yield ": keep-alive\n\n"


@app.get("/v1/feed/stream", tags=["frontend"])
async def feed_stream(request: Request):
    """Server-Sent Events endpoint — browser subscribes once and receives
    every new event pushed by Pathway in real time.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _sse_subscribers.append(queue)

    async def cleanup():
        if queue in _sse_subscribers:
            _sse_subscribers.remove(queue)

    async def event_stream():
        try:
            async for chunk in _sse_generator(queue):
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            await cleanup()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering
        },
    )


@app.get("/v1/frontend/feed", tags=["frontend"])
def get_feed():
    """Snapshot of the current buffer — used for initial page load."""
    return list(latest_news)


@app.get("/v1/generate_report", tags=["intel"])
def generate_report():
    """Generate a Gemini SITREP from the current buffer."""
    if not latest_news:
        raise HTTPException(status_code=400, detail="No intelligence data in buffer yet.")
    try:
        report = generate_sitrep(latest_news)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Report generation failed: {exc}") from exc
    return {"report": report}


@app.get("/v1/generate_report/pdf", tags=["intel"])
def generate_report_pdf():
    """Generate a SITREP and return it as a downloadable PDF file.

    The PDF is rendered server-side using fpdf2 with full FlashPoint
    branding: classification banner, coloured section headings,
    source summary table, and a numbered footer.
    """
    if not latest_news:
        raise HTTPException(status_code=400, detail="No intelligence data in buffer yet.")
    try:
        pdf_bytes = generate_pdf_bytes(list(latest_news))
    except Exception as exc:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=503, detail=f"PDF generation failed: {exc}") from exc

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"SITREP_{ts}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Chat endpoint ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []


@app.post("/v1/chat", tags=["intel"])
async def chat(req: ChatRequest):
    """Accept a user message and stream back a Gemini response via SSE.

    The client POSTs JSON, receives a ``text/event-stream`` response where
    each SSE ``data:`` line contains one token chunk, and a final
    ``data: [DONE]`` sentinel closes the stream.
    """
    import google.generativeai as genai
    import os
    from dotenv import load_dotenv
    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-flash-latest")

    # Build the conversation history for multi-turn context
    context_items = "\n".join(
        f"- {d.get('text','')} [{d.get('source','')}]"
        for d in list(latest_news)[-20:]   # last 20 feed items as context
    )
    system = (
        "You are FLASHPOINT, an AI intelligence analyst. "
        "You have access to the following recent intelligence feed:\n"
        f"{context_items}\n\n"
        "Answer the analyst's question concisely and factually. "
        "If the answer is not in the feed, say so."
    )

    # Reconstruct history for multi-turn
    history_text = "\n".join(
        f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
        for m in req.history[-6:]  # keep last 3 turns
    )
    full_prompt = f"{system}\n\n{history_text}\nUser: {req.message}\nAssistant:"

    async def token_stream() -> AsyncGenerator[str, None]:
        try:
            response = model.generate_content(full_prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    payload = json.dumps({"token": chunk.text})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0)   # yield to event loop
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Static mount (must be LAST — catches everything else) ─────────────
if _ASSETS_DIR.is_dir():
    app.mount("/assets",  StaticFiles(directory=str(_ASSETS_DIR)),  name="assets")
if _THEMES_DIR.is_dir():
    app.mount("/themes",  StaticFiles(directory=str(_THEMES_DIR)),  name="themes")
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend dir not found at %s — static serving disabled.", _FRONTEND_DIR)

