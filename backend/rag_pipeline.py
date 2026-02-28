"""RAG Pipeline: Embedding & Document Store

Responsibilities:
- Transform raw Pathway data stream into RAG-compatible format
- Embed documents using a lightweight SentenceTransformer model
- Expose a DocumentStore for semantic nearest-neighbour retrieval
"""

import pathway as pw
from pathway.stdlib.indexing.nearest_neighbors import BruteForceKnnFactory
from pathway.xpacks.llm.document_store import DocumentStore
from pathway.xpacks.llm.embedders import SentenceTransformerEmbedder


def build_rag_pipeline(combined_stream) -> DocumentStore:
    """Build RAG pipeline with embedding-based document retrieval.

    Steps:
    1. Rename ``text`` → ``data`` and pack provenance into ``_metadata``.
    2. Initialise a SentenceTransformer embedder (all-MiniLM-L6-v2, 384-dim).
    3. Wire up a brute-force KNN retriever over the embedded documents.
    4. Return the ready-to-query DocumentStore.

    Args:
        combined_stream: Pathway table with columns
            [source, text, url, timestamp, bias].

    Returns:
        DocumentStore: Initialised store ready to answer retrieval queries.
    """
    # ── Reshape stream to match DocumentStore expectations ──────────────
    rag_stream = combined_stream.select(
        # Primary content field used for embedding
        data=pw.this.text,

        # Bundle provenance into a metadata dictionary
        _metadata=pw.apply(
            lambda src, url, ts, bias: {
                "source":    src,
                "url":       url,
                "timestamp": ts,
                "bias":      bias,
            },
            pw.this.source,
            pw.this.url,
            pw.this.timestamp,
            pw.this.bias,
        ),
    )

    # ── Embedder: 22M-param model, optimised for semantic similarity ────
    embedder = SentenceTransformerEmbedder(model="all-MiniLM-L6-v2")

    # ── Retriever: brute-force KNN (O(n) per query, fine for datasets <1M) ──
    retriever_factory = BruteForceKnnFactory(embedder=embedder)

    # ── DocumentStore: indexes documents and serves retrieval queries ───
    document_store = DocumentStore(
        docs=rag_stream,
        retriever_factory=retriever_factory,
        parser=None,    # Raw text — no extra parsing needed
        splitter=None,  # Treat each document as an atomic unit
    )

    print("✅ RAG Pipeline built successfully.")
    return document_store


# ── Helpers consumed by the query service ──────────────────────────────

def get_context(documents) -> str:
    """Concatenate retrieved document texts into a single context string.

    Args:
        documents: List of document dicts containing a ``text`` key.

    Returns:
        Space-joined string of all document texts.
    """
    return " ".join(str(doc["text"]) for doc in documents)


@pw.udf
def build_prompts_udf(documents, query) -> str:
    """Pathway UDF: construct a zero-shot QA prompt for the LLM.

    Args:
        documents: Retrieved context documents (list of dicts).
        query:     User's natural-language question.

    Returns:
        Formatted prompt string ready for LLM consumption.
    """
    context = get_context(documents)
    return (
        f"Given the following documents:\n{context}\n"
        f"Answer this query: {query}"
    )
