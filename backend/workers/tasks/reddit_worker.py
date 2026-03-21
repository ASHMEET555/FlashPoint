"""Reddit Worker - Poll Reddit API for posts

Fetches posts from configured subreddits using Reddit's public JSON API.
"""

import requests
import hashlib
from datetime import datetime
from pathlib import Path
import json
from config.celery_config import celery_app
from models.redis_client import is_duplicate, RedisPubSub
from models.database import SessionLocal, Event


def load_reddit_config():
    """Load Reddit config from data_sources.json"""
    config_path = Path(__file__).parent.parent.parent.parent / "data" / "data_sources.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        reddit_sources = config.get("reddit_sources", [])
        if reddit_sources:
            return reddit_sources[0]  # First config
        return {}
    except Exception as e:
        print(f"⚠️ Failed to load Reddit config: {e}")
        return {}


@celery_app.task(name="tasks.reddit_worker.fetch_reddit")
def fetch_reddit():
    """Fetch posts from Reddit"""
    config = load_reddit_config()
    
    if not config.get("enabled", True):
        return {"status": "disabled"}
    
    subreddits = config.get("subreddits", ["worldnews", "geopolitics"])
    post_limit = config.get("post_limit", 50)
    
    # Join subreddits with +
    subreddit_string = "+".join(subreddits)
    url = f"https://www.reddit.com/r/{subreddit_string}/new.json?limit={post_limit}"
    
    headers = {
        'User-Agent': 'FlashPointEngine/2.0 (Macintosh; Intel Mac OS X 10_15_7)'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 429:
            print("⚠️ Reddit rate limited")
            return {"status": "rate_limited"}
        
        if response.status_code != 200:
            return {"status": "error", "code": response.status_code}
        
        data = response.json()
        posts = data.get('data', {}).get('children', [])
        
        db = SessionLocal()
        pubsub = RedisPubSub()
        new_posts = 0
        
        for item in posts:
            post = item.get('data', {})
            
            # Extract content
            title = post.get('title', '').strip()
            is_text_post = post.get('is_self', False)
            body = post.get('selftext', '').strip() if is_text_post else ""
            full_text = f"{title}\n{body}" if body else title
            
            # Compute hash
            content_hash = hashlib.sha256(full_text.encode()).hexdigest()
            
            # Check duplicate
            if is_duplicate(content_hash):
                continue
            
            # Create event
            event = Event(
                source="Reddit",
                text=full_text,
                url=f"https://reddit.com{post.get('permalink')}",
                timestamp=datetime.fromtimestamp(post.get('created_utc', 0)),
                bias="Varied",
                content_hash=content_hash
            )
            
            db.add(event)
            new_posts += 1
            
            # Publish to stream
            pubsub.publish({
                "type": "event",
                "source": "Reddit",
                "text": full_text[:200] + "..." if len(full_text) > 200 else full_text,
                "url": event.url,
                "timestamp": event.timestamp.isoformat(),
                "bias": "Varied"
            })
            
            # Queue for processing
            from workers.tasks.processor import process_event
            process_event.delay(event.id)
        
        db.commit()
        db.close()
        
        print(f"✅ Reddit: {new_posts} new posts")
        return {"status": "success", "new_posts": new_posts}
        
    except Exception as e:
        print(f"❌ Reddit fetch error: {e}")
        return {"status": "error", "message": str(e)}
