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
import json
from datetime import datetime
from pathlib import Path
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

# ========== DATA SOURCES CONFIG ==========
_CONFIG_PATH = Path(__file__).parent.parent / "data" / "data_sources.json"
_config_cache = None
_config_last_load = None


def load_data_sources_config(force_reload=False):
    """Load data sources from JSON config with caching and hot-reload support."""
    global _config_cache, _config_last_load
    
    try:
        # Check if we need to reload
        if not force_reload and _config_cache is not None:
            if _config_last_load and _CONFIG_PATH.exists():
                mtime = datetime.fromtimestamp(_CONFIG_PATH.stat().st_mtime)
                if mtime <= _config_last_load:
                    return _config_cache
        
        # Load fresh config
        with open(_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        _config_cache = config
        _config_last_load = datetime.now()
        
        print(f"✅ Loaded data sources config (version {config['config']['version']})")
        return config
        
    except Exception as e:
        print(f"⚠️ Error loading config: {e}, using fallback")
        return {"rss_feeds": [], "news_sources": [{"name": "GNews", "enabled": True}], 
                "reddit_sources": [], "telegram_sources": []}


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
    """Build unified multi-source intelligence stream using JSON configuration.
    
    Loads sources from data/data_sources.json with hot-reload support.
    Returns:
        Pathway table: Unified event stream [source, text, url, timestamp, bias]
    """
    
    # Load configuration
    config = load_data_sources_config()
    streams = []
    
    # ========== SOURCE 1: NEWS API ==========
    for news_config in config.get("news_sources", []):
        if not news_config.get("enabled", True):
            continue
        try:
            t_news = pw.io.python.read(
                NewsSource(
                    NEWS_API_KEY, 
                    query=news_config.get("query", "world"),
                    polling_interval=news_config.get("polling_interval", 60)
                ),
                schema=InputSchema, 
                name=f"{news_config['name']} Source",
                max_backlog_size=10
            )
            streams.append(t_news)
            print(f"✅ Enabled: {news_config['name']}")
        except Exception as e:
            print(f"⚠️ Failed to load {news_config['name']}: {e}")
   
    # ========== SOURCE 2: RSS FEEDS (JSON-based) ==========
    rss_tables = []
    for rss_config in config.get("rss_feeds", []):
        if not rss_config.get("enabled", True):
            continue
        try:
            t_rss = pw.io.python.read(
                RssSource(
                    url=rss_config["url"], 
                    source=rss_config["name"], 
                    bias_tag=rss_config.get("bias", "Neutral")
                ),
                schema=InputSchema, 
                name=f"{rss_config['name']} RSS",
                max_backlog_size=10
            )
            rss_tables.append(t_rss)
            print(f"✅ Enabled: {rss_config['name']} RSS")
        except Exception as e:
            print(f"⚠️ Failed to load {rss_config.get('name', 'RSS')}: {e}")
    
    # Merge all RSS feeds
    if rss_tables:
        t_rss_combined = rss_tables[0]
        if len(rss_tables) > 1:
            t_rss_combined = t_rss_combined.concat_reindex(*rss_tables[1:])
        streams.append(t_rss_combined)
    
    # ========== SOURCE 3: TELEGRAM ==========
    for tg_config in config.get("telegram_sources", []):
        if not tg_config.get("enabled", True):
            continue
        try:
            # Extract channel handles and build bias tag dictionary
            channels = [ch["handle"] for ch in tg_config.get("channels", [])]
            bias_tags = {ch["handle"]: ch.get("bias", "Independent") 
                        for ch in tg_config.get("channels", [])}
            
            t_telegram = pw.io.python.read(
                TelegramSource(
                    api_hash=TELEGRAM_API_HASH, 
                    api_id=TELEGRAM_API_ID, 
                    phone=TELEGRAM_PHONE,
                    channels=channels,
                    bias_tags=bias_tags,
                    backfill_limit=tg_config.get("backfill_messages", 20)
                ),
                schema=InputSchema,
                mode="streaming",
                name="Telegram Source",
                max_backlog_size=10
            )
            streams.append(t_telegram)
            print(f"✅ Enabled: Telegram ({len(channels)} channels)")
        except Exception as e:
            print(f"⚠️ Failed to load Telegram: {e}")
    
    # ========== SOURCE 4: REDDIT ==========
    for reddit_config in config.get("reddit_sources", []):
        if not reddit_config.get("enabled", True):
            continue
        try:
            t_reddit = pw.io.python.read(
                RedditSource(
                    subreddits=reddit_config.get("subreddits", ["worldnews", "geopolitics"]),
                    post_limit=reddit_config.get("post_limit", 50),
                    polling_interval=reddit_config.get("polling_interval", 60)
                ),
                schema=InputSchema,
                mode="streaming",
                name="Reddit Source", 
                max_backlog_size=10
            )
            streams.append(t_reddit)
            print(f"✅ Enabled: Reddit ({len(reddit_config.get('subreddits', []))} subreddits)")
        except Exception as e:
            print(f"⚠️ Failed to load Reddit: {e}")

    # ========== FINAL MERGE ==========
    if not streams:
        raise ValueError("No data sources enabled! Check data_sources.json")
        
    combined_stream = streams[0]
    if len(streams) > 1:
        combined_stream = combined_stream.concat_reindex(*streams[1:])
 
    print(f"✅ Pipeline ready with {len(streams)} active sources")
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

