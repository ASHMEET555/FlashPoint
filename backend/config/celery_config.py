"""Celery Configuration

Task queue for background jobs:
- Data source polling (RSS, Reddit, News API)
- Real-time streaming (Telegram)
- Periodic scraping (CFR conflicts, commodity prices)
- Processing pipeline (embeddings, NER)
"""

from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

# Celery broker (RabbitMQ or Redis)
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Initialize Celery app
celery_app = Celery(
    "flashpoint",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "tasks.rss_worker",
        "tasks.reddit_worker",
        "tasks.news_worker",
        "tasks.telegram_worker",
        "tasks.conflict_worker",
        "tasks.commodity_worker",
        "tasks.processor"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes warning
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Scheduled tasks (Beat)
celery_app.conf.beat_schedule = {
    # RSS feeds - every 5 minutes
    "fetch-rss-feeds": {
        "task": "tasks.rss_worker.fetch_all_rss",
        "schedule": 300.0,  # 5 minutes
    },
    
    # Reddit - every 1 minute
    "fetch-reddit-posts": {
        "task": "tasks.reddit_worker.fetch_reddit",
        "schedule": 60.0,  # 1 minute
    },
    
    # News API - every 10 minutes
    "fetch-news-api": {
        "task": "tasks.news_worker.fetch_news",
        "schedule": 600.0,  # 10 minutes
    },
    
    # CFR Conflicts - every 12 hours
    "scrape-conflicts": {
        "task": "tasks.conflict_worker.scrape_conflicts",
        "schedule": crontab(hour="*/12"),  # Every 12 hours
    },
    
    # Commodity Prices - every 3 hours
    "fetch-commodity-prices": {
        "task": "tasks.commodity_worker.fetch_commodities",
        "schedule": crontab(hour="*/3"),  # Every 3 hours
    },
}

# Queue routing
celery_app.conf.task_routes = {
    "tasks.rss_worker.*": {"queue": "data_ingestion"},
    "tasks.reddit_worker.*": {"queue": "data_ingestion"},
    "tasks.news_worker.*": {"queue": "data_ingestion"},
    "tasks.telegram_worker.*": {"queue": "realtime"},
    "tasks.conflict_worker.*": {"queue": "scraping"},
    "tasks.commodity_worker.*": {"queue": "scraping"},
    "tasks.processor.*": {"queue": "processing"},
}
