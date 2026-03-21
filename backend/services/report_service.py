"""Report Service — Intelligence SITREP Generator

Responsibility:
- Build a structured intelligence briefing prompt from the live news buffer
- Query Google Gemini to synthesise the prompt into a SITREP (Markdown)
- Render the Markdown into a branded PDF and return the raw bytes

Public API
----------
    generate_sitrep(news_buffer) -> str   — returns raw Markdown string
    generate_pdf_bytes(news_buffer) -> bytes — Markdown → branded PDF
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv
from fpdf import FPDF

logger = logging.getLogger(__name__)

# ── OpenRouter setup ──────────────────────────────────────────────────
load_dotenv()
_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# To a real free model slug, e.g.:
_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite:free")# ── Prompt template ───────────────────────────────────────────────────
_PROMPT_TEMPLATE = """\
TASK: Synthesize the provided 'Raw Intel' into a professional intelligence briefing.

CONSTRAINTS:
1. Use ONLY the provided text below. Do not invent facts, names, or events.
2. Tone: Objective, journalistic, concise.
3. Cite the source name in brackets [Source] after every claim.
4. Reply in **Markdown only**. Use ##, ###, -, and **bold** formatting freely.
5. USE ASCII CHARACTERS ONLY. DO NOT USE UNICODE CHARACTERS.

RAW INTEL:
{context}

REQUIRED SECTIONS (use these exact ## headings):
## Global Situation Summary
## Key Developments
## Narrative Divergence
## Outlook
"""


def _build_context(news_buffer: Iterable[dict[str, Any]]) -> str:
    lines = []
    for item in news_buffer:
        text   = item.get("text",   "N/A")
        source = item.get("source", "Unknown")
        bias   = item.get("bias",   "Neutral")
        lines.append(f"- {text} [{source}] ({bias})")
    return "\n".join(lines) if lines else "No intelligence items available."


def generate_sitrep(news_buffer: Iterable[dict[str, Any]]) -> str:
    """Call OpenRouter and return the raw Markdown SITREP string."""
    context  = _build_context(news_buffer)
    prompt   = _PROMPT_TEMPLATE.format(context=context)
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    text = response.choices[0].message.content if response.choices else None
    if not text:
        raise RuntimeError("OpenRouter returned an empty response.")
    return text


# ── PDF rendering ─────────────────────────────────────────────────────

_CYAN  = (0,   229, 255)
_AMBER = (255, 183, 3)
_WHITE = (224, 230, 237)
_DARK  = (13,  17,  23)
_GREY  = (100, 116, 139)


class _SitrepPDF(FPDF):
    def __init__(self, generated_at: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._generated_at = generated_at
        self.set_margins(14, 35, 14)
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        # Amber classification bar
        self.set_fill_color(*_AMBER)
        self.rect(0, 0, 210, 7, style="F")
        self.set_font("Courier", "B", 7)
        self.set_text_color(20, 20, 20)
        self.set_xy(0, 1)
        self.cell(210, 5, "FLASHPOINT INTELLIGENCE — UNCLASSIFIED // FOR OFFICIAL USE ONLY", align="C")

        # Dark title block
        self.set_fill_color(*_DARK)
        self.rect(0, 7, 210, 19, style="F")
        self.set_font("Courier", "B", 15)
        self.set_text_color(*_CYAN)
        self.set_xy(14, 9)
        self.cell(0, 8, "FLASHPOINT  INTEL SITREP")
        self.set_font("Courier", "", 7)
        self.set_text_color(*_GREY)
        self.set_xy(14, 19)
        self.cell(0, 4, f"Generated: {self._generated_at} UTC   |   Classification: UNCLASSIFIED")

        # Cyan rule
        self.set_draw_color(*_CYAN)
        self.set_line_width(0.4)
        self.line(14, 26, 196, 26)
        self.ln(4)

    def footer(self):
        self.set_y(-13)
        self.set_draw_color(*_GREY)
        self.set_line_width(0.25)
        self.line(14, self.get_y(), 196, self.get_y())
        self.set_font("Courier", "", 7)
        self.set_text_color(*_GREY)
        self.cell(0, 6, f"FLASHPOINT SITREP  |  Page {self.page_no()}/{{nb}}  |  DO NOT DISTRIBUTE", align="C")


def _safe(text: str) -> str:
    """Transliterate common unicode chars to ASCII equivalents for fpdf latin-1."""
    _UNICODE_MAP = str.maketrans({
        "\u2014": "--",   # em dash  —
        "\u2013": "-",    # en dash  –
        "\u2012": "-",    # figure dash
        "\u2010": "-",    # hyphen
        "\u2018": "'",    # left single quote  '
        "\u2019": "'",    # right single quote '
        "\u201c": '"',    # left double quote  "
        "\u201d": '"',    # right double quote "
        "\u2022": "*",    # bullet  •
        "\u00b7": ".",    # middle dot
        "\u2026": "...",  # ellipsis  …
        "\u00a0": " ",    # non-breaking space
        "\u2011": "-",    # non-breaking hyphen
    })
    text = text.translate(_UNICODE_MAP)
    # Drop anything still outside latin-1 (0x00-0xFF)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _md_to_pdf(pdf: FPDF, md_text: str) -> None:
    """Walk the Markdown token stream and render into the FPDF canvas."""
    # Strip fenced code fences (unlikely in SITREP but defensive)
    md_text = re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()

        # H2 heading  →  cyan bold section heading + underline
        if line.startswith("## "):
            pdf.ln(3)
            heading = _safe(line[3:].strip().upper())
            pdf.set_font("Courier", "B", 10)
            pdf.set_text_color(*_CYAN)
            pdf.cell(0, 6, heading, ln=True)
            pdf.set_draw_color(*_CYAN)
            pdf.set_line_width(0.25)
            pdf.line(14, pdf.get_y(), 196, pdf.get_y())
            pdf.ln(2)
            continue

        # H3 heading  →  grey bold sub-heading
        if line.startswith("### "):
            heading = _safe(line[4:].strip())
            pdf.set_font("Courier", "B", 9)
            pdf.set_text_color(*_GREY)
            pdf.cell(0, 5, heading, ln=True)
            pdf.ln(1)
            continue

        # Bullet / list item
        if re.match(r"^[-*]\s+", line):
            text = re.sub(r"^[-*]\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # strip bold markers
            text = _safe(text)
            pdf.set_font("Courier", "", 8.5)
            pdf.set_text_color(*_WHITE)
            pdf.set_x(18)
            pdf.multi_cell(0, 4.5, f"*  {text}")
            continue

        # Blank line
        if not line.strip():
            pdf.ln(2)
            continue

        # Normal paragraph (strip inline markdown)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", line)   # bold
        text = re.sub(r"\*(.+?)\*",     r"\1", text)   # italic
        text = re.sub(r"`(.+?)`",       r"\1", text)   # inline code
        text = _safe(text)
        pdf.set_font("Courier", "", 8.5)
        pdf.set_text_color(*_WHITE)
        pdf.set_x(14)
        pdf.multi_cell(0, 4.5, text)


def generate_pdf_bytes(news_buffer: Iterable[dict[str, Any]]) -> bytes:
    """Generate a Markdown SITREP via Gemini, then render it to PDF bytes."""
    items        = list(news_buffer)
    md_text      = generate_sitrep(items)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d  %H:%M")

    pdf = _SitrepPDF(generated_at=generated_at)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Source summary block
    if items:
        counts = Counter(d.get("source", "Unknown") for d in items)
        pdf.set_font("Courier", "B", 8)
        pdf.set_text_color(*_CYAN)
        pdf.cell(0, 5, "INTELLIGENCE SOURCES", ln=True)
        pdf.set_draw_color(*_CYAN)
        pdf.set_line_width(0.2)
        pdf.line(14, pdf.get_y(), 196, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("Courier", "", 8)
        pdf.set_text_color(*_WHITE)
        for src, cnt in counts.most_common():
            pdf.cell(0, 4, _safe(f"  *  {src}  ({cnt})"), ln=True)
        pdf.ln(5)

    # Render the Markdown body
    _md_to_pdf(pdf, md_text)

    # Closing banner
    pdf.ln(4)
    pdf.set_fill_color(*_AMBER)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Courier", "B", 7)
    pdf.cell(0, 6, "END OF REPORT  —  FLASHPOINT INTELLIGENCE  —  UNCLASSIFIED // FOUO",
             align="C", fill=True, ln=True)

    return bytes(pdf.output())
