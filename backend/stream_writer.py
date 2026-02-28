"""Stream Writer: Pathway → FastAPI Bridge

Responsibility:
- Forward every event from the unified Pathway stream to the FastAPI
  backend (port 8000) via an HTTP POST so the frontend can poll it.

This is intentionally a thin module — all routing and enrichment
(geolocation, buffering, report generation) happen inside ``api.py``.
"""

import pathway as pw

# ── Constants ─────────────────────────────────────────────────────────
API_STREAM_URL = "http://localhost:8000/v1/stream"


def start_stream_writer(stream) -> None:
    """Register a Pathway HTTP writer that POSTs stream events to the API.

    Each row emitted by ``stream`` is serialised as JSON and sent to the
    FastAPI ``/v1/stream`` endpoint, which buffers it for frontend polling.

    Args:
        stream: Pathway table with columns
            [source, text, url, timestamp, bias].
    """
    pw.io.http.write(
        table=stream,
        url=API_STREAM_URL,
        method="POST",
        format="json",
    )
    print(f"✅ Stream writer registered → {API_STREAM_URL}")
