"""Query Service: HTTP Intake → Retrieval → LLM Inference → Response

Responsibilities:
- Expose a REST endpoint (POST /v1/query) via a Pathway webserver
- Retrieve top-K relevant documents from the RAG document store
- Build LLM prompts from retrieved context + user query
- Stream LLM responses back to the HTTP client
"""

import os

import pathway as pw
from pathway.xpacks.llm import llms
from pathway.xpacks.llm.document_store import DocumentStore

from rag_pipeline import build_prompts_udf

from dotenv import load_dotenv # Add this
import pathway as pw
from pathway.xpacks.llm import llms

load_dotenv() # Add this
# ── Schema ────────────────────────────────────────────────────────────
class QuerySchema(pw.Schema):
    """Incoming query payload from the REST endpoint."""
    messages: str


# ── Constants ─────────────────────────────────────────────────────────
QUERY_HOST = "0.0.0.0"
QUERY_PORT = 8011
TOP_K = 5                   # Number of documents to retrieve per query
AUTOCOMMIT_MS = 50          # Batch queries every 50 ms


def build_query_service(document_store: DocumentStore):
    """Wire up the full query pipeline and return the HTTP writer.

    Pipeline stages:
    1. Start Pathway HTTP webserver on ``QUERY_PORT``.
    2. Accept POST /v1/query payloads matching ``QuerySchema``.
    3. Perform semantic retrieval (top-K documents) from the store.
    4. Join queries with their retrieved context.
    5. Construct zero-shot QA prompts via ``build_prompts_udf``.
    6. Run LLM inference (Gemini 2.0 Flash Lite via OpenRouter).
    7. Return the writer callable to send responses back to clients.

    Args:
        document_store: Initialised DocumentStore from ``rag_pipeline``.

    Returns:
        writer: Pathway HTTP writer — call ``writer(response_table)`` to
                flush results back to waiting HTTP clients.
    """
    # ── Stage 1: HTTP webserver ────────────────────────────────────────
    webserver = pw.io.http.PathwayWebserver(host=QUERY_HOST, port=QUERY_PORT)

    # ── Stage 2: REST connector ────────────────────────────────────────
    queries, writer = pw.io.http.rest_connector(
        webserver=webserver,
        route="/v1/query",
        schema=QuerySchema,
        autocommit_duration_ms=AUTOCOMMIT_MS,
        delete_completed_queries=False,   # Retain query history
    )

    # Normalise query shape and set retrieval parameters
    queries = queries.select(
        query=pw.this.messages,
        k=TOP_K,
        metadata_filter=None,         # Retrieve from all sources
        filepath_globpattern=None,    # No file-path filtering
    )

    # ── Stage 3: Document retrieval ────────────────────────────────────
    retrieved = document_store.retrieve_query(queries)
    retrieved = retrieved.select(docs=pw.this.result)

    # ── Stage 4: Join query + context ─────────────────────────────────
    queries_with_context = queries + retrieved

    # ── Stage 5: Prompt construction ──────────────────────────────────
    prompts = queries_with_context + queries_with_context.select(
        prompts=build_prompts_udf(pw.this.docs, pw.this.query)
    )

    # ── Stage 6: LLM inference ────────────────────────────────────────
    model = llms.OpenAIChat(
        model="openrouter/free", # Match the new model here
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,
    )

    response = prompts.select(
        *pw.this.without(pw.this.query, pw.this.prompts, pw.this.docs),
        result=model(llms.prompt_chat_single_qa(pw.this.prompts)),
    )

    # ── Stage 7: Write response back to HTTP client ───────────────────
    writer(response)

    print(f"✅ Query service configured on port {QUERY_PORT}.")
    return writer
