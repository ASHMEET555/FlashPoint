"""Report Service — Intelligence SITREP Generator

Responsibility:
- Build a structured intelligence briefing prompt from the live news buffer
- Query Google Gemini to synthesise the prompt into a SITREP
- Return the report as a plain-text string

Public API
----------
    generate_sitrep(news_buffer: Iterable[dict]) -> str
        Accepts the current event buffer and returns a formatted report.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Gemini setup ──────────────────────────────────────────────────────
load_dotenv()
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=_GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-flash-latest")


# ── Prompt template ───────────────────────────────────────────────────
_PROMPT_TEMPLATE = """\
TASK: Synthesize the provided 'Raw Intel' into a professional News Briefing.

CONSTRAINTS:
1. Use ONLY the provided text below. Do NOT fill in missing data like names, dates, or events not present.
2. Tone: Objective, Journalistic, Concise.
3. Cite the source name in brackets [Source] for every claim.
4. Reply in plain text, do not give response in markdown.

RAW INTEL:
{context}

REQUIRED OUTPUT FORMAT:
## Global Situation Summary
[Write a 2-3 sentence executive summary of the provided text]

## Key Developments
- [Category/Region]: [Detail] [Source]
- [Category/Region]: [Detail] [Source]

## Outlook
[Short forecast based *only* on the provided trends]
"""


def _build_context(news_buffer: Iterable[dict[str, Any]]) -> str:
    """Format buffer items into a numbered context block for the prompt."""
    lines = []
    for item in news_buffer:
        text   = item.get("text",   "N/A")
        source = item.get("source", "Unknown")
        bias   = item.get("bias",   "Neutral")
        lines.append(f"- {text} [{source}] ({bias})")
    return "\n".join(lines) if lines else "No intelligence items available."


def generate_sitrep(news_buffer: Iterable[dict[str, Any]]) -> str:
    """Generate a SITREP from the current news buffer via Gemini.

    Args:
        news_buffer: Iterable of event dicts with keys
            [text, source, bias, url, timestamp].

    Returns:
        Plain-text intelligence report string.

    Raises:
        RuntimeError: If Gemini returns an empty or error response.
    """
    context = _build_context(news_buffer)
    prompt  = _PROMPT_TEMPLATE.format(context=context)

    logger.debug("Sending SITREP prompt to Gemini (%d chars)", len(prompt))

    response = _model.generate_content(prompt)

    if not response or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text
