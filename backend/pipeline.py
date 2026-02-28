"""Pipeline Orchestrator — Pathway RAG Intelligence Pipeline

Wires together all pipeline stages in order:

    ┌─────────────────────────────────────────────┐
    │  data_registry  →  multi-source event stream │
    │  stream_writer  →  push events to FastAPI    │
    │  rag_pipeline   →  embed + index documents   │
    │  query_service  →  REST query → LLM response │
    └─────────────────────────────────────────────┘

Run this file directly to start the Pathway engine:
    python pipeline.py

The FastAPI server is started separately via:
    python main.py
"""

import pathway as pw

from data_registry import get_data_stream
from stream_writer import start_stream_writer
from rag_pipeline import build_rag_pipeline
from query_service import build_query_service


def run() -> None:
    """Assemble and launch the full intelligence pipeline.

    Stages
    ------
    1. **Data collection** – pull from all live sources (news, RSS,
       Reddit, Telegram) into a unified Pathway stream.
    2. **Stream forwarding** – POST every event to the FastAPI backend
       so the frontend can poll the latest feed.
    3. **RAG setup** – embed documents and build the KNN document store.
    4. **Query service** – start the HTTP server, handle queries, run
       LLM inference, and stream responses back to callers.
    5. **Event loop** – block until interrupted (Ctrl-C).
    """
    # ── Stage 1: Data collection ──────────────────────────────────────
    stream = get_data_stream()

    # ── Stage 2: Forward stream to FastAPI (port 8000) ───────────────
    start_stream_writer(stream)

    # ── Stage 3: Build RAG document store ────────────────────────────
    document_store = build_rag_pipeline(stream)

    # ── Stage 4: Start query service (port 8011) ─────────────────────
    build_query_service(document_store)

    # ── Stage 5: Run Pathway event loop ──────────────────────────────
    pw.run()


if __name__ == "__main__":
    run()

