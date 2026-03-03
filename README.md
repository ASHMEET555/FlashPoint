
# ⚡ FlashPoint: Real-Time Geopolitical Intelligence Platform

> **"While other AI models tell you what happened yesterday, FlashPoint tells you what is happening right now."**

### 🎥 [Watch the Demo Video Here](https://youtu.be/lqzr3LzJZWU)

---

## 🚨 The Problem: The "Knowledge Cutoff" in Crisis

Decision-makers (Governments, NGOs, Logistics) face a critical gap during rapidly evolving crises:

1. **News Lags:** Mainstream media takes 30-60 minutes to verify and publish.
2. **AI Hallucinates:** Standard LLMs have a knowledge cutoff or rely on slow browsing tools.
3. **Noise Overload:** Human analysts cannot manually filter thousands of Telegram messages per minute.

---

## 🛡️ The Solution: FlashPoint

**FlashPoint** is a **Live RAG (Retrieval Augmented Generation)** engine that listens to the raw pulse of the world — Telegram channels, Reddit threads, and News Wires — in real-time.

It uses **Pathway** to ingest, embed, and index streaming data instantly, allowing an AI LLM to answer strategic questions based on events that happened **seconds ago**.

The backend is a **FastAPI** service that serves both the REST API and a fully static HTML/CSS/JS dashboard — no separate frontend server needed. The Pathway engine runs as a parallel process, continuously updating the RAG context and pushing events over SSE.

---

### ✨ Key Features

- **📡 Multi-Source Intel** — Aggregates live data from **Telegram** (raw speed), **Reddit** (human intel), **GNews** and **RSS feeds** (verified reporting).
- **⚖️ Narrative Divergence Meter** — Bias detection that contrasts Western (BBC/NYT) vs. Eastern (RT/CGTN) framing on the same event, calculated over a rolling window of the last 50 items.
- **📍 Live Geopolitical Hotspot Map** — spaCy NER auto-extracts locations from text; map markers scale **proportionally** to how frequently a location is mentioned.
- **🔴 Real-Time SSE Feed** — New events are pushed to the browser instantly via Server-Sent Events; newest item animates to the top of the live feed.
- **🤖 Streaming AI Chat** — Ask the AI anything; it responds token-by-token with a live typing effect, grounded in the most recent 20 feed events.
- **📄 Automated SITREP Reports (PDF)** — Gemini generates structured intelligence briefs downloadable as PDF directly from the browser.
- **⚡ Zero-DB Architecture** — No vector database to manage. Pathway handles streaming embedding and retrieval entirely in-memory.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Sources                          │
│  Telegram · Reddit · GNews API · RSS Feeds · Simulation │
└───────────────────┬─────────────────────────────────────┘
                    │  pw.io.python.read()
                    ▼
┌─────────────────────────────────────────────────────────┐
│              Pathway Streaming Engine  (pipeline.py)    │
│  SentenceTransformerEmbedder → DocumentStore (KNN)      │
│  → query_service  (port 8011, OpenRouter/Gemini)        │
│  → stream_writer  (POST /v1/stream → FastAPI)           │
└───────────────────┬─────────────────────────────────────┘
                    │  HTTP POST /v1/stream
                    ▼
┌─────────────────────────────────────────────────────────┐
│            FastAPI Server  (api.py, port 8000)          │
│  geo_extractor  — spaCy NER + Nominatim geocoding       │
│  report_service — Gemini SITREP generation              │
│  SSE broadcast  — asyncio.Queue fan-out to browsers     │
│  StaticFiles    — serves frontend/web/ at "/"           │
└───────────────────┬─────────────────────────────────────┘
                    │  SSE / REST / Static files
                    ▼
┌─────────────────────────────────────────────────────────┐
│         Browser Dashboard  (frontend/web/)              │
│  EventSource feed · Leaflet map · Bias meter · Chat     │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Streaming Engine** | [Pathway](https://pathway.com) — live ETL, embedding, KNN index |
| **Backend API** | FastAPI + uvicorn — async REST + SSE |
| **RAG Inference** | OpenRouter → `google/gemini-2.0-flash-lite` (Pathway query service) |
| **AI Chat / SITREP** | Google Gemini (`gemini-flash-latest`) via `google-generativeai` |
| **NER / Geocoding** | spaCy `en_core_web_sm` + OSM Nominatim |
| **Frontend** | Vanilla HTML/CSS/JS — no framework, no build step |
| **Map** | Leaflet.js v1.9.4 — dark CartoDB tiles, proportional circle markers |
| **PDF Reports** | jsPDF 2.5.1 (client-side, CDN) |
| **Connectors** | `Telethon` (Telegram MTProto), `requests` (Reddit/GNews), `feedparser` (RSS) |
| **Deployment** | Docker Compose |

---

## 📂 Project Structure

```text
FlashPoint/
├── backend/
│   ├── main.py              # Entry point — uvicorn on port 8000
│   ├── pipeline.py          # Pathway orchestrator (run separately)
│   ├── api.py               # FastAPI routes (SSE feed, chat, report, health)
│   ├── geo_extractor.py     # spaCy NER + Nominatim geocoding service
│   ├── report_service.py    # Gemini SITREP generation service
│   ├── rag_pipeline.py      # Pathway DocumentStore + embedding pipeline
│   ├── query_service.py     # Pathway HTTP query intake → LLM → response
│   ├── stream_writer.py     # Pathway → FastAPI bridge with startup retry
│   ├── data_registry.py     # Source connector registry
│   ├── auth_telegram.py     # Telegram MTProto authentication
│   ├── connectors/
│   │   ├── telegram_src.py
│   │   ├── reddit_src.py
│   │   ├── news_src.py
│   │   ├── rss_src.py
│   │   └── sim_src.py       # Simulation source (dummy.jsonl)
│   └── Dockerfile
├── frontend/
│   └── web/                 # Static dashboard (served by FastAPI)
│       ├── index.html       # Three-column command dashboard
│       ├── styles.css       # Dark cyber theme + SSE animations
│       └── app.js           # SSE feed, map, bias meter, streaming chat
├── data/
│   └── dummy.jsonl          # 20 realistic geopolitical test events
├── docker-compose.yaml
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for containerised deployment)
- Telegram API ID & Hash — [my.telegram.org](https://my.telegram.org)
- [Google Gemini API key](https://aistudio.google.com/app/apikey)
- [GNews API key](https://gnews.io)
- [OpenRouter API key](https://openrouter.ai) (for Pathway RAG queries)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/Reaper-ai/FlashPoint.git
cd FlashPoint
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env and fill in all API keys
```

4. **Run the FastAPI server** (Terminal 1)
```bash
cd backend && python main.py
```

5. **Run the Pathway pipeline** (Terminal 2)
```bash
cd backend && python pipeline.py
```

6. **Open the dashboard**

Navigate to [http://localhost:8000](http://localhost:8000)

> **Offline / demo mode:** Set `USE_DUMMY = true` in `frontend/web/app.js` to load the built-in test feed without a running backend.

### Docker (full stack)

```bash
docker-compose up --build
```

Authenticate Telegram on first run by entering your phone number and the OTP sent to the Telegram app.

---

## 🕹️ Usage

1. Open the dashboard at [http://localhost:8000](http://localhost:8000).
2. Watch the **Live Intel Feed** (left column) — new events slide in from the top as they arrive.
3. The **Geopolitical Hotspot Map** (centre) shows circle markers sized by how frequently each location appears in the stream.
4. The **Narrative Balance** bar (right column) updates in real time based on the last 50 events.
5. Type a question in the **AI Chat** panel — the response streams back token-by-token.
6. Click **Generate Report** to produce a Gemini-authored PDF SITREP of current conditions.

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/v1/stream` | Pathway → API event ingestion |
| `GET` | `/v1/feed/stream` | SSE stream of live events (EventSource) |
| `GET` | `/v1/frontend/feed` | Snapshot of last 100 events (JSON) |
| `GET` | `/v1/generate_report` | Trigger Gemini SITREP generation |
| `POST` | `/v1/chat` | SSE-streaming LLM chat |
| `GET` | `/` | Static dashboard (index.html) |

---

## 👥 Team

- **Gaurav Upreti** — Backend, Pathway Pipeline, API
- **Ashmeet Singh Sandhu** — Frontend, Data Connectors & Design

---

*Built with ❤️ using [Pathway](https://pathway.com).*
