"""Data Registry: Multi-Source Intelligence Collection Pipeline

Orchestrates all data sources into unified Pathway event stream:
- News API (GNews) - news articles
- RSS Feeds - state media (Russia Today, SCMP) & western media (NYTimes, BBC)
- Reddit - public discussion forums
- Telegram - real-time messaging channels
- Simulation - test data from JSONL file

All sources normalized into unified InputSchema for downstream processing.
"""

import pathway as pw
import pandas as pd
from connectors.telegram_src import TelegramSource
from connectors.reddit_src import RedditSource
from connectors.news_src import NewsSource
from connectors.sim_src import SimulationSource
from connectors.rss_src import RssSource
import os
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()  # This loads the variables from .env

# ========== ENVIRONMENT CREDENTIALS ==========
NEWS_API_KEY = os.getenv("GNEWS_API_KEY")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ========== UNIFIED INPUT SCHEMA ==========
# All data sources normalized to this schema for downstream processing
class InputSchema(pw.Schema):
    """Standardized event schema across all sources
    
    Attributes:
        source (str): Data origin (NewsAPI, Reddit, Telegram, RSS, Simulation)
        text (str): Main content (article, post, message)
        url (str): Source link for reference/verification
        timestamp (float): Unix timestamp of publication/ingestion
        bias (str): Source bias tag (Pro-Russia, US/Western, Independent, etc.)
    """
    source: str
    text: str
    url: str
    timestamp: float
    bias: str

def get_data_stream():
    """Build unified multi-source intelligence stream
    
    Process:
    1. Initialize individual source connectors
    2. Normalize each to InputSchema
    3. Concatenate into single Pathway table
    4. Return combined stream for RAG pipeline
    
    Sources:
    - News API: Global news (60-sec polling interval)
    - RSS Feeds: State media & Western media (300-sec polling)
    - Reddit: Public forums (60-sec polling)
    - Telegram: Real-time channels (streaming mode)
    
    Returns:
        Pathway table: Unified event stream [source, text, url, timestamp, bias]
    """
    
    # ========== SOURCE 1: NEWS API ==========
    # GNews aggregator: collects global news articles
    # Polling: 60 seconds (hourly API limits apply)
    t_news = pw.io.python.read(
        NewsSource(NEWS_API_KEY, query="world", polling_interval=60),
        schema=InputSchema, 
        name="NewsAPI Source",
        max_backlog_size=10  # Buffer max 10 items before processing
    )
   
    # ========== SOURCE 2: RSS FEEDS ==========
    # Dynamically load feeds from data/rss_feeds.csv
    try:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "rss_feeds.csv")
        df_rss = pd.read_csv(csv_path)
        rss_tables = []
        
        for _, row in df_rss.iterrows():
            name = row.get("source", "Unknown RSS")
            rss_tables.append(
                pw.io.python.read(
                    RssSource(
                        url=row["url"], 
                        source=name, 
                        bias_tag=row.get("bias", "Neutral")
                    ),
                    schema=InputSchema, 
                    name=f"{name} Feed",
                    max_backlog_size=10
                )
            )

        # Merge all RSS tables if any exist
        if rss_tables:
            t_rss_combined = rss_tables[0]
            if len(rss_tables) > 1:
                t_rss_combined = t_rss_combined.concat_reindex(*rss_tables[1:])
        else:
            # Fallback if CSV is empty
            print("⚠️ No RSS feeds found in CSV.")
            t_rss_combined = None

    except Exception as e:
        print(f"⚠️ Failed to load RSS feeds from CSV: {e}")
        t_rss_combined = None
    
    # ========== SOURCE 3: TELEGRAM ==========
    # Real-time messaging from curated channels
    # Streaming mode: receives messages as they arrive (no polling)
    t_telegram = pw.io.python.read(
        TelegramSource(api_hash=TELEGRAM_API_HASH, api_id=TELEGRAM_API_ID, phone=TELEGRAM_PHONE),
        schema=InputSchema,
        mode="streaming",  # Live event subscription
        name="Telegram Source",
        max_backlog_size=10
    )
    
    # ========== SOURCE 4: REDDIT ==========
    # Public forum discussions across relevant subreddits
    # Streaming mode: monitors new posts
    t_reddit = pw.io.python.read(
        RedditSource(),
        schema=InputSchema,
        mode="streaming",
        name="Reddit Source", 
        max_backlog_size=10
    )

    # ========== MERGE RSS FEEDS ==========
    # (Already handled above in SOURCE 2)
    
    # ========== FINAL MERGE: ALL SOURCES ==========
    # Combine News, Reddit, RSS, and Telegram into unified stream
    streams = [t_news, t_reddit, t_telegram]
    if t_rss_combined:
        streams.append(t_rss_combined)
        
    combined_stream = streams[0].concat_reindex(*streams[1:])
 
    return combined_stream

def get_simulation_stream():
    """Load test data stream from JSONL file for development/testing
    
    Use case:
    - Test pipeline without external API dependencies
    - Replay scenarios for debugging
    - Load-test infrastructure
    
    Returns:
        Pathway table: Simulation events in InputSchema format
    """
    sim_path = "data/dummy.jsonl"
    
    # Initialize simulation source with 10-second inter-event delay
    t_sim = pw.io.python.read(
        SimulationSource(file_path=sim_path, interval=10),
        schema=InputSchema,
        autocommit_duration_ms=1000,  # Process batches every 1 second
        name="Simulation Source",
        max_backlog_size=10
    )

    pw.io.csv
    return t_sim

