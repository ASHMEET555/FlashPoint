#!/bin/bash

# FlashPoint V2 Startup Script
# Starts all required services in the correct order

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          FlashPoint V2 - Startup Manager                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "[1/5] Starting infrastructure services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check Redis
echo -n "  Checking Redis... "
if docker exec flashpoint_redis redis-cli ping > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
    exit 1
fi

# Check PostgreSQL
echo -n "  Checking PostgreSQL... "
if docker exec flashpoint_postgres pg_isready -U flashpoint > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
    exit 1
fi

# Check Qdrant
echo -n "  Checking Qdrant... "
if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
    exit 1
fi

echo ""
echo "[2/5] Initializing database..."
cd backend
python init_infra.py || {
    echo "❌ Database initialization failed"
    exit 1
}
cd ..

echo ""
echo "[3/5] Starting Celery worker..."
celery -A backend.celery_config worker \
    -l info \
    -Q data_ingestion,processing,scraping,realtime \
    --detach \
    --pidfile=/tmp/celery_worker.pid \
    --logfile=logs/celery_worker.log

echo "✅ Celery worker started (PID file: /tmp/celery_worker.pid)"

echo ""
echo "[4/5] Starting Celery beat (scheduler)..."
celery -A backend.celery_config beat \
    -l info \
    --detach \
    --pidfile=/tmp/celery_beat.pid \
    --logfile=logs/celery_beat.log

echo "✅ Celery beat started (PID file: /tmp/celery_beat.pid)"

echo ""
echo "[5/5] Starting FastAPI server..."
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    🚀 All Services Ready                   ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  Frontend:      http://localhost:8000                      ║"
echo "║  API Docs:      http://localhost:8000/docs                 ║"
echo "║  Qdrant UI:     http://localhost:6333/dashboard            ║"
echo "║                                                            ║"
echo "║  Logs:                                                     ║"
echo "║    - Celery Worker: logs/celery_worker.log                 ║"
echo "║    - Celery Beat:   logs/celery_beat.log                   ║"
echo "║                                                            ║"
echo "║  Stop services: ./scripts/stop.sh                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Start FastAPI (foreground)
cd backend
python main.py
