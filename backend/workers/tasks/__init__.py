"""Tasks package - Celery workers for data ingestion and processing"""

from tasks.rss_worker import fetch_all_rss, fetch_single_rss
from tasks.reddit_worker import fetch_reddit
from tasks.news_worker import fetch_news
from tasks.conflict_worker import scrape_conflicts
from tasks.commodity_worker import fetch_commodities
from tasks.telegram_worker import start_telegram_stream
from tasks.processor import process_event, batch_process_events

__all__ = [
    "fetch_all_rss",
    "fetch_single_rss",
    "fetch_reddit",
    "fetch_news",
    "scrape_conflicts",
    "fetch_commodities",
    "start_telegram_stream",
    "process_event",
    "batch_process_events"
]
