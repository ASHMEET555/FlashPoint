# FlashPoint Development Guide

Complete guide for developers contributing to FlashPoint.

---

## Development Setup

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **Git**
- **Code Editor** (VS Code recommended)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/Reaper-ai/FlashPoint.git
cd FlashPoint

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Start Development Environment

```bash
# Start infrastructure
docker-compose up -d

# Initialize database
python backend/init_infra.py

# Start workers (terminal 1)
celery -A backend.config.celery_config worker --loglevel=info

# Start beat scheduler (terminal 2)
celery -A backend.config.celery_config beat --loglevel=info

# Start FastAPI server (terminal 3)
uvicorn backend.main:app --reload --port 8000
```

Or use the startup script:

```bash
./start.sh
```

---

## Project Structure

```
FlashPoint/
├── backend/
│   ├── api.py                  # FastAPI routes
│   ├── main.py                 # Entry point
│   ├── init_infra.py          # DB init script
│   ├── models/
│   │   ├── database.py        # SQLAlchemy models
│   │   └── redis_client.py    # Redis utilities
│   ├── services/
│   │   ├── rag_service.py     # LangChain RAG
│   │   ├── report_service.py  # SITREP generation
│   │   ├── commodity_service.py
│   │   ├── conflict_service.py
│   │   └── geo_extractor.py
│   ├── workers/tasks/
│   │   ├── rss_worker.py
│   │   ├── reddit_worker.py
│   │   ├── news_worker.py
│   │   ├── telegram_worker.py
│   │   ├── conflict_worker.py
│   │   ├── commodity_worker.py
│   │   └── processor.py
│   └── config/
│       ├── celery_config.py
│       └── auth_telegram.py
├── frontend/web/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── js/                     # ES6 modules
├── data/
│   └── data_sources.json       # Source configuration
├── docs/                       # Documentation
├── logs/                       # Celery logs
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── start.sh
└── stop.sh
```

---

## Development Workflow

### Making Changes

1. **Create feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make changes**

3. **Test locally**
```bash
# Run linting
flake8 backend/

# Check types
mypy backend/

# Format code
black backend/
```

4. **Commit**
```bash
git add .
git commit -m "feat: add new feature"
```

5. **Push and create PR**
```bash
git push origin feature/your-feature-name
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Add tests
- `chore:` - Maintenance

---

## Adding a New Data Source

### 1. Telegram Channel

**File**: `data/data_sources.json`

```json
{
  "telegram_channels": [
    {
      "username": "new_channel",
      "bias": "Neutral",
      "enabled": true
    }
  ]
}
```

**Test**:
```bash
# Restart workers
./stop.sh && ./start.sh

# Check logs
tail -f logs/celery-worker.log | grep telegram_worker
```

### 2. Custom Worker

**File**: `backend/workers/tasks/custom_worker.py`

```python
from celery import shared_task
from models.database import async_session, Event
from models.redis_client import is_duplicate, RedisPubSub
import asyncio

@shared_task(name='custom_worker.fetch_data')
def fetch_data():
    """Fetch data from custom source"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_fetch_async())

async def _fetch_async():
    # Your scraping logic here
    data = await fetch_from_source()
    
    # Check for duplicates
    if await is_duplicate(data['text']):
        return
    
    # Store in database
    async with async_session() as session:
        event = Event(
            source="CustomSource",
            text=data['text'],
            url=data.get('url'),
            # ... other fields
        )
        session.add(event)
        await session.commit()
    
    # Broadcast to SSE
    pubsub = RedisPubSub()
    await pubsub.publish('flashpoint:events', event.to_dict())
```

**Register in `backend/config/celery_config.py`**:

```python
beat_schedule = {
    'fetch-custom': {
        'task': 'custom_worker.fetch_data',
        'schedule': 600,  # 10 minutes
    },
}
```

---

## Database Operations

### Add New Column

1. **Update model** in `backend/models/database.py`:

```python
class Event(Base):
    # ... existing columns
    new_field = Column(String, nullable=True)
```

2. **Create migration** (manual for now):

```sql
ALTER TABLE events ADD COLUMN new_field VARCHAR;
```

3. **Restart services**

### Query Data

```python
from backend.models.database import async_session, Event
from sqlalchemy import select

async def query_events():
    async with async_session() as session:
        result = await session.execute(
            select(Event).where(Event.source == "Reuters")
        )
        events = result.scalars().all()
        return events
```

---

## Testing

### Manual Testing

```bash
# Test API endpoint
curl http://localhost:8000/health

# Test SSE stream
curl -N http://localhost:8000/api/events/stream

# Test RAG chat
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What happened today?"}'
```

### Unit Tests (TODO)

```python
# tests/test_workers.py
import pytest
from backend.workers.tasks import rss_worker

def test_rss_fetch():
    result = rss_worker.fetch_single_rss("https://example.com/feed")
    assert result is not None
```

Run tests:
```bash
pytest tests/
```

---

## Debugging

### Enable Debug Logging

**File**: `backend/main.py`

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug Celery Task

```python
# In any worker file
import logging
logger = logging.getLogger(__name__)

@shared_task
def my_task():
    logger.debug("Task started")
    logger.info("Processing data")
    logger.error("Error occurred")
```

### Inspect Database

```bash
# Connect to PostgreSQL
docker exec -it flashpoint-postgres psql -U flashpoint

# List tables
\dt

# Query events
SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;

# Check hypertables
SELECT * FROM timescaledb_information.hypertables;
```

### Inspect Redis

```bash
# Connect to Redis
docker exec -it flashpoint-redis redis-cli

# View keys
KEYS *

# Get cached data
GET recent_events

# Monitor pub/sub
SUBSCRIBE flashpoint:events
```

### Inspect Qdrant

```bash
# Check collection
curl http://localhost:6333/collections/flashpoint_events

# Count vectors
curl http://localhost:6333/collections/flashpoint_events/points/count
```

---

## Performance Optimization

### Database

1. **Add indexes**:
```sql
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_source ON events(source);
```

2. **Optimize TimescaleDB**:
```sql
SELECT set_chunk_time_interval('events', INTERVAL '1 day');
SELECT add_retention_policy('events', INTERVAL '30 days');
```

### Celery

**File**: `backend/config/celery_config.py`

```python
app.conf.worker_prefetch_multiplier = 4
app.conf.worker_max_tasks_per_child = 1000
app.conf.task_soft_time_limit = 240  # 4 minutes
app.conf.task_time_limit = 300  # 5 minutes
```

### Redis

```bash
# Check memory usage
docker exec flashpoint-redis redis-cli INFO memory

# Optimize if needed
docker exec flashpoint-redis redis-cli CONFIG SET maxmemory 512mb
docker exec flashpoint-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

## Code Style

### Python

- **Formatter**: Black
- **Linter**: Flake8
- **Type Checker**: MyPy

```bash
# Format code
black backend/

# Lint
flake8 backend/ --max-line-length 100

# Type check
mypy backend/
```

### JavaScript

- **Style**: Standard ES6
- **No build step**: Keep it simple
- **Modules**: Use ES6 import/export

---

## Environment Variables

**File**: `.env`

```bash
# Database
DATABASE_URL=postgresql://flashpoint:password@localhost:5432/flashpoint

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# OpenRouter (RAG)
OPENROUTER_API_KEY=your_key

# Telegram
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE=your_phone

# GNews API
GNEWS_API_KEY=your_key

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## Deployment

### Docker Production Build

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build:
```bash
docker build -t flashpoint:latest .
```

### Docker Compose Production

**File**: `docker-compose.prod.yml`

```yaml
version: '3.8'
services:
  app:
    image: flashpoint:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
      - qdrant
```

---

## Troubleshooting Common Issues

### Issue: Celery workers not starting

**Solution**:
```bash
# Check Celery app initialization
celery -A backend.config.celery_config inspect active

# Restart workers
./stop.sh && ./start.sh
```

### Issue: Database connection errors

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string in .env
echo $DATABASE_URL
```

### Issue: Redis connection errors

**Solution**:
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker exec flashpoint-redis redis-cli PING
```

### Issue: Frontend not loading

**Solution**:
```bash
# Check FastAPI is serving static files
curl http://localhost:8000/

# Check browser console for errors
# Open DevTools → Console
```

---

## Contributing Guidelines

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** locally
5. **Document** your changes
6. **Submit** a pull request

### PR Checklist

- [ ] Code follows project style
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts

---

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Celery Docs**: https://docs.celeryq.dev
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **LangChain Docs**: https://python.langchain.com
- **Qdrant Docs**: https://qdrant.tech/documentation/

---

*Happy coding! 🚀*
