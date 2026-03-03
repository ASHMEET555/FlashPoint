"""Stream Writer: Pathway → FastAPI Bridge

Responsibility:
- Forward every event from the unified Pathway stream to the FastAPI
  backend (port 8000) via an HTTP POST so the frontend can poll it.
- Wait for the FastAPI server to be ready before Pathway starts writing
  (FastAPI takes a few seconds to initialise; without this the first
  batch of events is lost).
"""

import time
import requests
import pathway as pw

# ── Constants ─────────────────────────────────────────────────────────
API_STREAM_URL = "http://localhost:8000/v1/stream"
HEALTH_URL     = "http://localhost:8000/health"
RETRY_INTERVAL = 2   # seconds between readiness checks
MAX_RETRIES    = 30  # give up after ~60 s


def wait_for_api(health_url: str = HEALTH_URL) -> bool:
    """Block until the FastAPI server responds to /health or we time out.

    Returns:
        True if the server became ready, False if we exhausted retries.
    """
    print("⏳ Waiting for FastAPI to be ready…")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(health_url, timeout=2)
            if resp.status_code == 200:
                print(f"✅ FastAPI ready after {attempt * RETRY_INTERVAL}s")
                return True
        except requests.ConnectionError:
            pass
        time.sleep(RETRY_INTERVAL)

    print(f"❌ FastAPI did not respond after {MAX_RETRIES * RETRY_INTERVAL}s — proceeding anyway.")
    return False


def start_stream_writer(stream) -> None:
    """Wait for FastAPI, then register a Pathway HTTP writer.

    Each row emitted by ``stream`` is serialised as JSON and POSTed to
    ``/v1/stream``, which buffers it and broadcasts it to SSE subscribers.

    Args:
        stream: Pathway table with columns
            [source, text, url, timestamp, bias].
    """
    wait_for_api()

    pw.io.http.write(
        table=stream,
        url=API_STREAM_URL,
        method="POST",
        format="json",
    )
    print(f"✅ Stream writer registered → {API_STREAM_URL}")

