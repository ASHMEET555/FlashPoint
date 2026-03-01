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

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
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


# ── Routes ────────────────────────────────────────────────────────────

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
async def generate_report():
    """Generate a SITREP from the current buffer via OpenRouter."""
    if not latest_news:
        raise HTTPException(status_code=400, detail="No intelligence data in buffer yet.")
    try:
        items = list(latest_news)
        loop  = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, generate_sitrep, items)
    except Exception as exc:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=503, detail=f"Report generation failed: {exc}") from exc
    return {"report": report}


@app.get("/v1/generate_report/pdf", tags=["intel"])
async def generate_report_pdf():
    """Generate a SITREP and return it as a downloadable PDF file."""
    if not latest_news:
        raise HTTPException(status_code=400, detail="No intelligence data in buffer yet.")
    try:
        items     = list(latest_news)
        loop      = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, generate_pdf_bytes, items)
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
    """Proxy user message to the Pathway RAG query service (port 8011).

    The RAG pipeline does retrieval over the live document store, builds
    a context-grounded prompt, and runs LLM inference via OpenRouter.
    The result is returned as an SSE stream of token chunks so the
    frontend typing effect works unchanged.
    """
    PATHWAY_QUERY_URL = "http://localhost:8011/v1/query"

    async def token_stream() -> AsyncGenerator[str, None]:
        try:
            # Pathway's webserver closes the connection after sending the
            # response body (HTTP/1.0 style), which makes httpx raise
            # RemoteProtocolError even though the full body was received.
            # Use a raw stream request so we can read whatever bytes arrived.
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    async with client.stream(
                        "POST",
                        PATHWAY_QUERY_URL,
                        json={"messages": req.message},
                    ) as resp:
                        raw = await resp.aread()
                except httpx.RemoteProtocolError as e:
                    # Connection closed after body sent — still try to use
                    # whatever was buffered in the response object
                    raw = getattr(e, "response", None)
                    raw = raw.content if raw else b""

                if not raw:
                    yield f"data: {json.dumps({'error': 'Empty response from RAG pipeline'})}\n\n"
                    return

                try:
                    data   = json.loads(raw)
                    answer = data.get("result", "") if isinstance(data, dict) else str(data)
                except Exception:
                    answer = raw.decode("utf-8", errors="replace")

                if not answer:
                    answer = "No relevant intelligence found in the document store."

                # Stream word-by-word so the frontend typing effect fires
                for word in answer.split(" "):
                    yield f"data: {json.dumps({'token': word + ' '})}\n\n"
                    await asyncio.sleep(0.01)

        except httpx.HTTPStatusError as exc:
            logger.error("Pathway query service error: %s", exc)
            yield f"data: {json.dumps({'error': f'RAG service error: {exc.response.status_code}'})}\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Pipeline not running — start pipeline.py first'})}\n\n"
        except Exception as exc:
            logger.exception("Chat proxy error")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Static mount (must be LAST — catches everything else) ─────────────
if _ASSETS_DIR.is_dir():
    app.mount("/assets",  StaticFiles(directory=str(_ASSETS_DIR)),  name="assets")
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend dir not found at %s — static serving disabled.", _FRONTEND_DIR)

