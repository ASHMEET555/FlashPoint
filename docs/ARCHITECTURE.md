# FlashPoint Architecture Documentation

## Overview

FlashPoint v2.0 uses a **native Python async stack** with distributed workers, persistent storage, and real-time streaming. This architecture replaced the original Pathway-based implementation to provide complete control over the data pipeline.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   DATA SOURCES (53 total)               │
├─────────────────────────────────────────────────────────┤
│  • RSS Feeds (18)        - Every 5 minutes              │
│  • Telegram (25)         - Real-time streaming          │
│  • Reddit (10)           - Every 1 minute               │
│  • GNews API             - Every 10 minutes             │
│  • CFR Conflict Tracker  - Every 12 hours               │
│  • Commodity APIs        - Every 3 hours                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              CELERY WORKERS (Task Queue)                │
├─────────────────────────────────────────────────────────┤
│  Queue: data_ingestion                                  │
│    - rss_worker.fetch_all_rss()                         │
│    - reddit_worker.fetch_reddit()                       │
│    - news_worker.fetch_news()                           │
│                                                         │
│  Queue: realtime                                        │
│    - telegram_worker.start_telegram_stream()            │
│                                                         │
│  Queue: scraping                                        │
│    - conflict_worker.scrape_conflicts()                 │
│    - commodity_worker.fetch_commodities()               │
│                                                         │
│  Queue: processing                                      │
│    - processor.process_event() (embeddings)             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              PROCESSING PIPELINE                        │
├─────────────────────────────────────────────────────────┤
│  1. Deduplication                                       │
│     - SHA256 content hashing                            │
│     - Redis cache (24-hour TTL)                         │
│     - Prevents duplicate processing                     │
│                                                         │
│  2. Embedding Generation                                │
│     - sentence-transformers: all-MiniLM-L6-v2           │
│     - 384-dimension vectors                             │
│     - Normalized embeddings                             │
│                                                         │
│  3. Storage                                             │
│     - PostgreSQL: Structured event data                 │
│     - Qdrant: Vector embeddings for RAG                 │
│                                                         │
│  4. Broadcasting                                        │
│     - Redis pub/sub: "flashpoint:events" channel       │
│     - Real-time SSE notifications                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  STORAGE LAYER                          │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL 15 + TimescaleDB                            │
│    • events table (hypertable, 1-day chunks)            │
│      - id, source, text, url, timestamp                 │
│      - bias, content_hash, entities, sentiment          │
│      - lat, lon, place, embedding_id                    │
│    • commodities table (hypertable, 1-hour chunks)      │
│      - symbol, name, rate, unit, timestamp              │
│    • conflicts table                                    │
│      - name, status, impact, severity, location         │
│                                                         │
│  Redis 7                                                │
│    • Cache (5-10 min TTL)                               │
│    • Deduplication hashes (24h TTL)                     │
│    • Pub/Sub channels for real-time events              │
│    • Rate limiting (token bucket)                       │
│                                                         │
│  Qdrant Vector Database                                 │
│    • Collection: flashpoint_events                      │
│    • Distance metric: COSINE                            │
│    • Dimensions: 384                                    │
│    • Payload: source, text, timestamp, metadata         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 FASTAPI SERVER (Port 8000)              │
├─────────────────────────────────────────────────────────┤
│  REST Endpoints:                                        │
│    GET  /health                   - Health check        │
│    GET  /api/events/recent        - Initial page load  │
│    GET  /api/events/stream        - SSE real-time feed │
│    POST /v1/chat                  - RAG chat (streaming)│
│    GET  /v1/generate_report       - SITREP (Markdown)  │
│    GET  /v1/generate_report/pdf   - SITREP (PDF)       │
│    GET  /api/commodities/latest   - Cached prices      │
│    GET  /api/conflicts/all        - CFR conflicts      │
│                                                         │
│  Services:                                              │
│    • rag_service.py      - LangChain + Qdrant          │
│    • report_service.py   - Gemini report generation    │
│    • commodity_service.py - Price caching              │
│    • conflict_service.py  - CFR scraping               │
│    • geo_extractor.py     - spaCy NER + geocoding      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               FRONTEND (ES6 Modules)                    │
├─────────────────────────────────────────────────────────┤
│  • feed.js         - EventSource SSE connection         │
│  • map.js          - Leaflet map with markers           │
│  • chat.js         - RAG chat with typing effect        │
│  • commodities.js  - Price widget                       │
│  • conflicts.js    - Conflict markers                   │
│  • reports.js      - SITREP generation UI               │
│  • utils.js        - Shared utilities                   │
└─────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Data Ingestion Layer

**Celery Workers** handle all data fetching:

- **RSS Worker** (`rss_worker.py`)
  - Schedule: Every 5 minutes
  - Uses `feedparser` to parse RSS/Atom feeds
  - Configurable via `data/data_sources.json`
  - 18 feeds currently configured

- **Reddit Worker** (`reddit_worker.py`)
  - Schedule: Every 1 minute
  - Uses Reddit public JSON API (no auth required)
  - Combines post title + selftext
  - 10 subreddits monitored

- **News Worker** (`news_worker.py`)
  - Schedule: Every 10 minutes
  - Uses GNews API (requires API key)
  - Fetches articles based on search query

- **Telegram Worker** (`telegram_worker.py`)
  - Real-time streaming with Telethon
  - Long-lived task, not scheduled
  - 25 channels configured
  - Bias tags per channel

- **Conflict Worker** (`conflict_worker.py`)
  - Schedule: Every 12 hours
  - Scrapes CFR Global Conflict Tracker
  - BeautifulSoup parsing
  - Extracts: name, status, severity, location

- **Commodity Worker** (`commodity_worker.py`)
  - Schedule: Every 3 hours
  - Fetches gold, silver, oil prices
  - Caches in Redis

### 2. Processing Pipeline

**Processor** (`processor.py`):

1. **Deduplication**
   - Generates SHA256 hash of content
   - Checks Redis for existing hash
   - 24-hour deduplication window

2. **Embedding**
   - Uses sentence-transformers library
   - Model: `all-MiniLM-L6-v2` (384-dim)
   - Lazy model loading
   - Normalized vectors

3. **Storage**
   - **PostgreSQL**: Structured data
   - **Qdrant**: Vector embeddings
   - Atomic transactions

4. **Broadcasting**
   - Publishes to Redis `flashpoint:events` channel
   - JSON-serialized event
   - Triggers SSE push to connected clients

### 3. Storage Layer

**PostgreSQL + TimescaleDB**:
- Automatic time-series partitioning
- Events table: 1-day chunks
- Commodities table: 1-hour chunks
- Efficient time-range queries

**Redis**:
- Multi-purpose caching layer
- Pub/sub for real-time events
- Deduplication tracking
- Rate limiting

**Qdrant**:
- Vector similarity search
- COSINE distance metric
- Metadata filtering
- Scalable to millions of vectors

### 4. API Layer

**FastAPI Server** (`api.py`):
- Async request handling
- SSE streaming with `StreamingResponse`
- Static file serving (frontend)
- CORS enabled for development

**RAG Service** (`rag_service.py`):
- **LangChain** orchestration
- **Qdrant** as retriever (top-10 docs)
- **OpenRouter** LLM (Llama 3.3 70B)
- Custom prompt template for geopolitical analysis
- Streaming token generation

### 5. Frontend

**Modular ES6 JavaScript**:
- No build step required
- `type="module"` in HTML
- Clean separation of concerns
- Each module handles one feature

**Real-time Updates**:
- EventSource API for SSE
- Automatic reconnection on disconnect
- Efficient DOM updates (prepend new cards)

---

## Data Flow Example

### Event Ingestion Flow

```
1. RSS Worker fetches new article
   ↓
2. Worker checks Redis for duplicate (SHA256)
   ↓ (if unique)
3. Store event in PostgreSQL
   ↓
4. Queue embedding task to processor
   ↓
5. Processor generates 384-dim vector
   ↓
6. Store vector in Qdrant with metadata
   ↓
7. Publish event to Redis pub/sub
   ↓
8. SSE connection streams to all browsers
   ↓
9. Frontend prepends card to feed
   ↓
10. Map updates hotspot marker
```

### RAG Query Flow

```
1. User types question in chat
   ↓
2. Frontend sends POST to /v1/chat
   ↓
3. RAG service embeds the question
   ↓
4. Qdrant retrieves top-10 similar events
   ↓
5. LangChain builds context prompt
   ↓
6. OpenRouter LLM generates response
   ↓
7. Tokens streamed back via SSE
   ↓
8. Frontend displays with typing effect
```

---

## Scalability

### Horizontal Scaling

- **Celery Workers**: Add more worker containers
- **PostgreSQL**: Read replicas for queries
- **Redis**: Redis Cluster or Sentinel
- **Qdrant**: Distributed mode with sharding

### Performance Tuning

1. **Database**
   - TimescaleDB automatic chunk pruning
   - Index on timestamp for range queries
   - VACUUM schedule

2. **Redis**
   - Optimize TTL values
   - Use pipelining for bulk operations
   - Monitor memory usage

3. **Qdrant**
   - Adjust HNSW parameters (M, ef_construct)
   - Use quantization for large collections
   - Batch vector uploads

4. **Celery**
   - Worker concurrency settings
   - Task prefetching (default: 4)
   - Result backend optimization

---

## Monitoring & Observability

### Logs

- **Celery**: `logs/celery-worker.log`, `logs/celery-beat.log`
- **FastAPI**: stdout (uvicorn)
- **Docker**: `docker-compose logs`

### Metrics (Future)

- Prometheus exporters
- Grafana dashboards
- Alert rules for failures

### Health Checks

- `/health` endpoint
- Database connectivity
- Redis connectivity
- Service status

---

## Security Considerations

1. **API Keys**: Use environment variables, never commit
2. **Database**: Use strong passwords, restrict network access
3. **CORS**: Restrict origins in production
4. **Rate Limiting**: Redis-based token bucket
5. **Input Validation**: Pydantic models for API requests
6. **SQL Injection**: SQLAlchemy parameterized queries

---

## Migration from Pathway

The original Pathway implementation was replaced to gain:

- **Full control** over pipeline stages
- **Persistent storage** (PostgreSQL vs in-memory)
- **Horizontal scalability** (Celery workers)
- **Better debugging** (explicit error handling)
- **Flexibility** (easy to add new sources)

See `docs/MIGRATION.md` for full migration details.

---

*Last Updated: March 2026*
