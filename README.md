# ⚡ FlashPoint v2.0: Real-Time Geopolitical Intelligence Platform

# ⚡ FlashPoint: Real-Time Geopolitical Intelligence Platform

> **"While other AI models tell you what happened yesterday, FlashPoint tells you what is happening right now."**

> **"While other AI models tell you what happened yesterday, FlashPoint tells you what is happening right now."**

**FlashPoint** is a production-ready intelligence aggregation and analysis platform that ingests data from 50+ sources in real-time, performs semantic analysis, and provides RAG-powered insights through an interactive dashboard.

### 🎥 [Watch the Demo Video Here](https://youtu.be/lqzr3LzJZWU)

[![Watch Demo](https://img.shields.io/badge/▶️_Watch_Demo-YouTube-red?style=for-the-badge)](https://youtu.be/lqzr3LzJZWU)

---

---

## 🚨 The Problem: The "Knowledge Cutoff" in Crisis

## 🎯 What It Does

Decision-makers (Governments, NGOs, Logistics) face a critical gap during rapidly evolving crises:

FlashPoint solves the **"Knowledge Cutoff"** problem in crisis intelligence:

1. **News Lags:** Mainstream media takes 30-60 minutes to verify and publish.

- **📡 Real-Time Ingestion**: Monitors 25 Telegram channels, 10 Reddit communities, 18 RSS feeds, and news APIs2. **AI Hallucinates:** Standard LLMs have a knowledge cutoff or rely on slow browsing tools.

- **🧠 Semantic Analysis**: Generates embeddings and stores in Qdrant vector database for intelligent retrieval3. **Noise Overload:** Human analysts cannot manually filter thousands of Telegram messages per minute.

- **🤖 RAG-Powered Chat**: Ask questions about current events with LangChain + OpenRouter LLM

- **📊 Visual Dashboard**: Live feed with Leaflet map, commodity prices, conflict tracking---

- **📄 Auto-Reports**: Generate intelligence SITREPs with one click (Markdown + PDF)

## 🛡️ The Solution: FlashPoint

---

**FlashPoint** is a **Live RAG (Retrieval Augmented Generation)** engine that listens to the raw pulse of the world — Telegram channels, Reddit threads, and News Wires — in real-time.

## ⚡ Quick Start

It uses **Pathway** to ingest, embed, and index streaming data instantly, allowing an AI LLM to answer strategic questions based on events that happened **seconds ago**.

### Prerequisites

- Docker & Docker ComposeThe backend is a **FastAPI** service that serves both the REST API and a fully static HTML/CSS/JS dashboard — no separate frontend server needed. The Pathway engine runs as a parallel process, continuously updating the RAG context and pushing events over SSE.

- Python 3.11+

- OpenRouter API key (free tier works)---

- Telegram API credentials (for Telegram sources)

### ✨ Key Features

### 1. Clone & Configure

- **📡 Multi-Source Intel** — Aggregates live data from **Telegram** (raw speed), **Reddit** (human intel), **GNews** and **RSS feeds** (verified reporting).

```bash- **⚖️ Narrative Divergence Meter** — Bias detection that contrasts Western (BBC/NYT) vs. Eastern (RT/CGTN) framing on the same event, calculated over a rolling window of the last 50 items.

git clone https://github.com/Reaper-ai/FlashPoint.git- **📍 Live Geopolitical Hotspot Map** — spaCy NER auto-extracts locations from text; map markers scale **proportionally** to how frequently a location is mentioned.

cd FlashPoint- **🔴 Real-Time SSE Feed** — New events are pushed to the browser instantly via Server-Sent Events; newest item animates to the top of the live feed.

- **🤖 Streaming AI Chat** — Ask the AI anything; it responds token-by-token with a live typing effect, grounded in the most recent 20 feed events.

# Copy environment template- **📄 Automated SITREP Reports (PDF)** — Gemini generates structured intelligence briefs downloadable as PDF directly from the browser.

cp .env.example .env- **⚡ Zero-DB Architecture** — No vector database to manage. Pathway handles streaming embedding and retrieval entirely in-memory.



# Edit .env with your credentials---

nano .env

```## 🏗️ Architecture



### 2. Start Infrastructure```

┌─────────────────────────────────────────────────────────┐

```bash│                   Data Sources                          │

# Start PostgreSQL, Redis, Qdrant│  Telegram · Reddit · GNews API · RSS Feeds · Simulation │

docker-compose up -d└───────────────────┬─────────────────────────────────────┘

                    │  pw.io.python.read()

# Verify services are healthy                    ▼

docker-compose ps┌─────────────────────────────────────────────────────────┐

```│              Pathway Streaming Engine  (pipeline.py)    │

│  SentenceTransformerEmbedder → DocumentStore (KNN)      │

### 3. Install Dependencies│  → query_service  (port 8011, OpenRouter/Gemini)        │

│  → stream_writer  (POST /v1/stream → FastAPI)           │

```bash└───────────────────┬─────────────────────────────────────┘

python -m venv .venv                    │  HTTP POST /v1/stream

source .venv/bin/activate  # Windows: .venv\Scripts\activate                    ▼

pip install -r requirements.txt┌─────────────────────────────────────────────────────────┐

```│            FastAPI Server  (api.py, port 8000)          │

│  geo_extractor  — spaCy NER + Nominatim geocoding       │

### 4. Initialize Database│  report_service — Gemini SITREP generation              │

│  SSE broadcast  — asyncio.Queue fan-out to browsers     │

```bash│  StaticFiles    — serves frontend/web/ at "/"           │

python backend/init_infra.py└───────────────────┬─────────────────────────────────────┘

```                    │  SSE / REST / Static files

                    ▼

### 5. Launch FlashPoint┌─────────────────────────────────────────────────────────┐

│         Browser Dashboard  (frontend/web/)              │

```bash│  EventSource feed · Leaflet map · Bias meter · Chat     │

./start.sh└─────────────────────────────────────────────────────────┘

``````



This starts:---

- Celery workers (data ingestion)

- Celery beat (task scheduler)## 🛠️ Tech Stack

- FastAPI server (http://localhost:8000)

| Layer | Technology |

**Open your browser**: http://localhost:8000|---|---|

| **Streaming Engine** | [Pathway](https://pathway.com) — live ETL, embedding, KNN index |

---| **Backend API** | FastAPI + uvicorn — async REST + SSE |

| **RAG Inference** | OpenRouter → `google/gemini-2.0-flash-lite` (Pathway query service) |

## 🏗️ Architecture| **AI Chat / SITREP** | Google Gemini (`gemini-flash-latest`) via `google-generativeai` |

| **NER / Geocoding** | spaCy `en_core_web_sm` + OSM Nominatim |

```| **Frontend** | Vanilla HTML/CSS/JS — no framework, no build step |

┌──────────────────────────────────────────────────────────┐| **Map** | Leaflet.js v1.9.4 — dark CartoDB tiles, proportional circle markers |

│                    DATA SOURCES                          │| **PDF Reports** | jsPDF 2.5.1 (client-side, CDN) |

│  RSS (18) │ Telegram (25) │ Reddit (10) │ News APIs     │| **Connectors** | `Telethon` (Telegram MTProto), `requests` (Reddit/GNews), `feedparser` (RSS) |

└────────────────────┬─────────────────────────────────────┘| **Deployment** | Docker Compose |

                     │

                     ▼---

┌──────────────────────────────────────────────────────────┐

│               CELERY WORKERS (Distributed)               │## 📂 Project Structure

│  RSS Worker (5min) │ Reddit (1min) │ News (10min)       │

│  Telegram (realtime) │ Conflicts (12h) │ Commodities    │```text

└────────────────────┬─────────────────────────────────────┘FlashPoint/

                     │├── backend/

                     ▼│   ├── main.py              # Entry point — uvicorn on port 8000

┌──────────────────────────────────────────────────────────┐│   ├── pipeline.py          # Pathway orchestrator (run separately)

│                 PROCESSING PIPELINE                      ││   ├── api.py               # FastAPI routes (SSE feed, chat, report, health)

│  Dedup (SHA256) → Embed (sentence-transformers)         ││   ├── geo_extractor.py     # spaCy NER + Nominatim geocoding service

│  → Store (PostgreSQL + Qdrant) → Publish (Redis)        ││   ├── report_service.py    # Gemini SITREP generation service

└────────────────────┬─────────────────────────────────────┘│   ├── rag_pipeline.py      # Pathway DocumentStore + embedding pipeline

                     ││   ├── query_service.py     # Pathway HTTP query intake → LLM → response

                     ▼│   ├── stream_writer.py     # Pathway → FastAPI bridge with startup retry

┌──────────────────────────────────────────────────────────┐│   ├── data_registry.py     # Source connector registry

│                   STORAGE LAYER                          ││   ├── auth_telegram.py     # Telegram MTProto authentication

│  PostgreSQL + TimescaleDB │ Qdrant │ Redis              ││   ├── connectors/

└────────────────────┬─────────────────────────────────────┘│   │   ├── telegram_src.py

                     ││   │   ├── reddit_src.py

                     ▼│   │   ├── news_src.py

┌──────────────────────────────────────────────────────────┐│   │   ├── rss_src.py

│                   FASTAPI SERVER                         ││   │   └── sim_src.py       # Simulation source (dummy.jsonl)

│  SSE Stream │ RAG Chat │ Reports │ Commodities          ││   └── Dockerfile

└────────────────────┬─────────────────────────────────────┘├── frontend/

                     ││   └── web/                 # Static dashboard (served by FastAPI)

                     ▼│       ├── index.html       # Three-column command dashboard

┌──────────────────────────────────────────────────────────┐│       ├── styles.css       # Dark cyber theme + SSE animations

│              FRONTEND (ES6 Modules)                      ││       └── app.js           # SSE feed, map, bias meter, streaming chat

│  Live Feed │ Leaflet Map │ Chat │ Commodities           │├── data/

└──────────────────────────────────────────────────────────┘│   └── dummy.jsonl          # 20 realistic geopolitical test events

```├── docker-compose.yaml

├── requirements.txt

### Key Technologies└── README.md

```

**Backend**:

- **FastAPI** - Async web framework---

- **Celery** - Distributed task queue

- **SQLAlchemy** - ORM with async support## 🚀 Getting Started

- **LangChain** - RAG framework

- **sentence-transformers** - Embeddings (all-MiniLM-L6-v2)### Prerequisites



**Storage**:- Python 3.10+

- **PostgreSQL 15 + TimescaleDB** - Time-series event storage- Docker & Docker Compose (for containerised deployment)

- **Redis 7** - Caching, deduplication, pub/sub- Telegram API ID & Hash — [my.telegram.org](https://my.telegram.org)

- **Qdrant** - Vector database (384-dim COSINE)- [Google Gemini API key](https://aistudio.google.com/app/apikey)

- [GNews API key](https://gnews.io)

**AI**:- [OpenRouter API key](https://openrouter.ai) (for Pathway RAG queries)

- **OpenRouter** - LLM API (Llama 3.3 70B)

- **LangChain** - RAG orchestration### Local Development

- **spaCy** - NER for entity extraction

1. **Clone the repository**

**Frontend**:```bash

- **Vanilla JavaScript** (ES6 modules)git clone https://github.com/Reaper-ai/FlashPoint.git

- **Leaflet.js** - Interactive mapscd FlashPoint

- **Server-Sent Events** - Real-time updates```



---2. **Install dependencies**

```bash

## 📁 Project Structurepip install -r requirements.txt

python -m spacy download en_core_web_sm

``````

FlashPoint/

├── backend/3. **Configure environment**

│   ├── api.py                    # FastAPI routes```bash

│   ├── main.py                   # Application entry pointcp .env.example .env

│   ├── init_infra.py            # Database initialization# Edit .env and fill in all API keys

│   ├── models/```

│   │   ├── database.py          # SQLAlchemy models

│   │   └── redis_client.py      # Redis utilities4. **Run the FastAPI server** (Terminal 1)

│   ├── services/```bash

│   │   ├── rag_service.py       # LangChain RAGcd backend && python main.py

│   │   ├── report_service.py    # SITREP generation```

│   │   ├── commodity_service.py # Price tracking

│   │   ├── conflict_service.py  # CFR scraping5. **Run the Pathway pipeline** (Terminal 2)

│   │   └── geo_extractor.py     # NER + geocoding```bash

│   ├── workers/tasks/cd backend && python pipeline.py

│   │   ├── rss_worker.py        # RSS polling```

│   │   ├── reddit_worker.py     # Reddit API

│   │   ├── news_worker.py       # GNews API6. **Open the dashboard**

│   │   ├── telegram_worker.py   # Telethon streaming

│   │   ├── conflict_worker.py   # CFR scrapingNavigate to [http://localhost:8000](http://localhost:8000)

│   │   ├── commodity_worker.py  # Price fetching

│   │   └── processor.py         # Embedding generation> **Offline / demo mode:** Set `USE_DUMMY = true` in `frontend/web/app.js` to load the built-in test feed without a running backend.

│   └── config/

│       ├── celery_config.py     # Celery configuration### Docker (full stack)

│       └── auth_telegram.py     # Telegram credentials

├── frontend/web/```bash

│   ├── index.html               # Main pagedocker-compose up --build

│   ├── app.js                   # Entry point```

│   └── js/

│       ├── feed.js              # SSE event streamAuthenticate Telegram on first run by entering your phone number and the OTP sent to the Telegram app.

│       ├── map.js               # Leaflet integration

│       ├── chat.js              # RAG chat interface---

│       ├── commodities.js       # Price widget

│       ├── conflicts.js         # Conflict markers## 🕹️ Usage

│       ├── reports.js           # SITREP generation

│       └── utils.js             # Shared utilities1. Open the dashboard at [http://localhost:8000](http://localhost:8000).

├── data/2. Watch the **Live Intel Feed** (left column) — new events slide in from the top as they arrive.

│   └── data_sources.json        # Source configuration (53 sources)3. The **Geopolitical Hotspot Map** (centre) shows circle markers sized by how frequently each location appears in the stream.

├── docker-compose.yml           # Infrastructure services4. The **Narrative Balance** bar (right column) updates in real time based on the last 50 events.

├── start.sh                     # One-command startup5. Type a question in the **AI Chat** panel — the response streams back token-by-token.

├── stop.sh                      # Graceful shutdown6. Click **Generate Report** to produce a Gemini-authored PDF SITREP of current conditions.

└── docs/                        # Documentation

```---



---## 🔌 API Endpoints



## 🎮 Usage| Method | Path | Description |

|---|---|---|

### Dashboard Features| `GET` | `/health` | Liveness probe |

| `POST` | `/v1/stream` | Pathway → API event ingestion |

1. **Live Feed** - Real-time event stream with SSE| `GET` | `/v1/feed/stream` | SSE stream of live events (EventSource) |

2. **Interactive Map** - Click markers to see event details| `GET` | `/v1/frontend/feed` | Snapshot of last 100 events (JSON) |

3. **RAG Chat** - Ask questions: *"What's happening in Gaza?"*| `GET` | `/v1/generate_report` | Trigger Gemini SITREP generation |

4. **Commodity Prices** - Gold, silver, oil prices (auto-refresh)| `POST` | `/v1/chat` | SSE-streaming LLM chat |

5. **Conflict Tracker** - CFR Global Conflict Tracker integration| `GET` | `/` | Static dashboard (index.html) |

6. **SITREP Generation** - One-click intelligence reports

---

### API Endpoints

## 👥 Team

```bash

# Health check- **Gaurav Upreti** — Backend, Pathway Pipeline, API

curl http://localhost:8000/health- **Ashmeet Singh Sandhu** — Frontend, Data Connectors & Design



# Recent events---

curl http://localhost:8000/api/events/recent?limit=10

*Built with ❤️ using [Pathway](https://pathway.com).*

# Event stream (SSE)
curl http://localhost:8000/api/events/stream

# RAG chat
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the latest developments in Ukraine?"}'

# Generate report
curl http://localhost:8000/v1/generate_report

# Commodities
curl http://localhost:8000/api/commodities/latest

# Conflicts
curl http://localhost:8000/api/conflicts/all
```

### Adding Data Sources

Edit `data/data_sources.json`:

```json
{
  "telegram_channels": [
    {
      "username": "new_channel",
      "bias": "Neutral",
      "enabled": true
    }
  ],
  "reddit_subreddits": ["worldnews"],
  "rss_feeds": [
    {
      "url": "https://example.com/feed.xml",
      "name": "Example News",
      "enabled": true
    }
  ]
}
```

Restart workers: `./stop.sh && ./start.sh`

---

## 🔧 Configuration

### Environment Variables

```bash
# PostgreSQL
DATABASE_URL=postgresql://flashpoint:password@localhost:5432/flashpoint

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# OpenRouter (for RAG)
OPENROUTER_API_KEY=your_key_here

# Telegram
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE=your_phone

# GNews API (optional)
GNEWS_API_KEY=your_key
```

### Worker Schedules

Edit `backend/config/celery_config.py`:

```python
beat_schedule = {
    'fetch-rss': {'task': 'rss_worker.fetch_all_rss', 'schedule': 300},  # 5 min
    'fetch-reddit': {'task': 'reddit_worker.fetch_reddit', 'schedule': 60},  # 1 min
    'fetch-news': {'task': 'news_worker.fetch_news', 'schedule': 600},  # 10 min
    # ...
}
```

---

## 📊 Monitoring

### View Logs

```bash
# Celery worker
tail -f logs/celery-worker.log

# Celery beat
tail -f logs/celery-beat.log

# Docker services
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f qdrant
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it flashpoint-postgres psql -U flashpoint

# Check events
SELECT COUNT(*) FROM events;
SELECT source, COUNT(*) FROM events GROUP BY source;
```

### Redis

```bash
# Connect to Redis
docker exec -it flashpoint-redis redis-cli

# Check keys
KEYS *
GET recent_events
```

---

## 🚀 Deployment

### Production Recommendations

1. **Use PostgreSQL managed service** (AWS RDS, DigitalOcean)
2. **Use Redis managed service** (Redis Cloud, AWS ElastiCache)
3. **Deploy Qdrant on K8s** or use Qdrant Cloud
4. **Run Celery workers as separate containers**
5. **Use HTTPS** with Let's Encrypt
6. **Set up monitoring** with Grafana + Prometheus
7. **Enable backups** for PostgreSQL

### Docker Deployment

```bash
# Build production image
docker build -t flashpoint:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See `docs/DEVELOPMENT.md` for development setup.

---

## 📄 License

MIT License - see LICENSE file

---

## 🙏 Credits

- **Pathway** (original RAG implementation, now replaced)
- **LangChain** for RAG orchestration
- **OpenRouter** for LLM access
- **CFR Global Conflict Tracker** for conflict data
- **Leaflet.js** for mapping
- All open source contributors

---

## 📚 Documentation

- [Architecture Details](docs/ARCHITECTURE.md)
- [Migration Guide](docs/MIGRATION.md)
- [Data Sources](docs/DATA_SOURCES.md)
- [Development Guide](docs/DEVELOPMENT.md)

---

## 🐛 Known Issues & Roadmap

See [GitHub Issues](https://github.com/Reaper-ai/FlashPoint/issues)

**Roadmap**:
- [ ] Twitter/X integration
- [ ] Sentiment analysis dashboard
- [ ] Multi-language support
- [ ] Mobile app
- [ ] GraphQL API

---

**Built with ❤️ for intelligence analysts, journalists, and decision-makers**

*FlashPoint v2.0 - Native Architecture (March 2026)*
