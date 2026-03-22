#!/bin/bash

# FlashPoint V2 Stop Script
# Gracefully stops all services

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          FlashPoint V2 - Shutdown Manager                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "[1/3] Stopping Celery worker..."
if [ -f /tmp/celery_worker.pid ]; then
    kill -TERM $(cat /tmp/celery_worker.pid) 2>/dev/null || true
    rm -f /tmp/celery_worker.pid
    echo "✅ Celery worker stopped"
else
    echo "⚠️  Celery worker PID file not found"
fi

echo ""
echo "[2/3] Stopping Celery beat..."
if [ -f /tmp/celery_beat.pid ]; then
    kill -TERM $(cat /tmp/celery_beat.pid) 2>/dev/null || true
    rm -f /tmp/celery_beat.pid
    echo "✅ Celery beat stopped"
else
    echo "⚠️  Celery beat PID file not found"
fi

echo ""
echo "[3/3] Stopping infrastructure services..."
docker-compose down

echo ""
echo "✅ All services stopped"
echo ""
echo "To restart: ./start.sh"
