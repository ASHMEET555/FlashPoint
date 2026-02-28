"""Entry Point — FastAPI Server

Starts the FlashPoint FastAPI backend via Uvicorn on port 8000.

Usage
-----
    python main.py

The Pathway RAG pipeline must be started separately:
    python pipeline.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
