"""Redis Client Configuration

Provides Redis connection for:
- Caching (commodity prices, conflicts)
- Deduplication (content hashes)
- Pub/Sub (real-time event streaming)
- Rate limiting
"""

import redis
import os
from dotenv import load_dotenv
import json
from typing import Optional, Any

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Redis clients
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
redis_binary = redis.from_url(REDIS_URL, decode_responses=False)  # For pub/sub


# ========== CACHE UTILITIES ==========

def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set cache with TTL (default 1 hour)"""
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        print(f"⚠️ Redis cache set error: {e}")
        return False


def cache_get(key: str) -> Optional[str]:
    """Get cached value"""
    try:
        return redis_client.get(key)
    except Exception as e:
        print(f"⚠️ Redis cache get error: {e}")
        return None


def cache_json_get(key: str) -> Optional[dict]:
    """Get cached JSON value"""
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        print(f"⚠️ Redis cache JSON get error: {e}")
        return None


def cache_delete(key: str) -> bool:
    """Delete cache key"""
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"⚠️ Redis cache delete error: {e}")
        return False


# ========== DEDUPLICATION ==========

def is_duplicate(content_hash: str, ttl: int = 86400) -> bool:
    """Check if content hash exists (dedup within 24 hours)"""
    try:
        key = f"dedup:{content_hash}"
        exists = redis_client.exists(key)
        if not exists:
            # Mark as seen
            redis_client.setex(key, ttl, "1")
            return False
        return True
    except Exception as e:
        print(f"⚠️ Redis dedup error: {e}")
        return False


# ========== PUB/SUB ==========

class RedisPubSub:
    """Redis Pub/Sub wrapper for event streaming"""
    
    def __init__(self, channel: str = "flashpoint:events"):
        self.channel = channel
        self.pubsub = redis_binary.pubsub()
    
    def publish(self, message: dict):
        """Publish message to channel"""
        try:
            redis_client.publish(self.channel, json.dumps(message))
        except Exception as e:
            print(f"⚠️ Redis publish error: {e}")
    
    def subscribe(self):
        """Subscribe to channel"""
        self.pubsub.subscribe(self.channel)
        return self.pubsub
    
    def unsubscribe(self):
        """Unsubscribe from channel"""
        self.pubsub.unsubscribe(self.channel)
    
    def listen(self):
        """Listen for messages (generator)"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    yield data
                except Exception as e:
                    print(f"⚠️ Redis message parse error: {e}")


# ========== RATE LIMITING ==========

def check_rate_limit(key: str, limit: int, window: int = 60) -> bool:
    """Check if rate limit exceeded (returns True if OK to proceed)"""
    try:
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, window)
        return current <= limit
    except Exception as e:
        print(f"⚠️ Redis rate limit error: {e}")
        return True  # Fail open


# ========== HEALTH CHECK ==========

def redis_health_check() -> bool:
    """Check Redis connection"""
    try:
        redis_client.ping()
        return True
    except Exception as e:
        print(f"⚠️ Redis health check failed: {e}")
        return False
