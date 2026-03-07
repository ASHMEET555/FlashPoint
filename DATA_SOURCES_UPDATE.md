# FlashPoint Data Sources Configuration Update

## 📋 Summary

Successfully refactored all data sources to use JSON-based configuration with proper handling of Reddit and Telegram sources. Added comprehensive list of conflict intelligence sources from `conflict_sources.json`.

---

## ✅ Changes Made

### 1. **Updated `data/data_sources.json`**
   - **Version**: 1.0 → 2.0
   - **RSS Feeds**: 6 → 18 sources
   - **Telegram Channels**: 0 → 25 channels with proper configuration
   - **Reddit Subreddits**: 3 → 10 subreddits
   - **Duplicate Handling**: Removed duplicates, unified naming conventions

#### New RSS Sources Added:
- Reuters World News
- AP News
- France 24
- DW News
- The Guardian World
- Kyiv Independent
- Ukraine Pravda
- Jerusalem Post
- Times of Israel
- Bellingcat (OSINT)
- Military Times
- Defense One

#### Telegram Configuration:
- **Total Channels**: 25
- **Regions Covered**:
  - Ukraine-Russia Conflict (8 channels)
  - Middle East (4 channels)
  - Global OSINT (13 channels)
- **Bias Tags**: Properly mapped for each channel (Pro Russia, Pro Ukraine, Independent OSINT, Middle East, etc.)
- **Format**: Structured with `handle`, `bias`, and `region` for each channel

#### Reddit Configuration:
- **Subreddits**: worldnews, geopolitics, news, breakingnews, politics, UkrainianConflict, syriancivilwar, YemenVoice, Israel_Palestine, intelligence
- **Post Limit**: 50 posts per poll
- **Polling Interval**: 60 seconds
- **Bias**: "Varied" (Reddit has mixed viewpoints)

---

### 2. **Refactored `backend/connectors/reddit_src.py`**

#### Old Approach:
```python
# Hardcoded constants
SUBREDDITS = "worldnews+geopolitics+news+breakingnews+..."
POST_LIMIT = 50
POLL_INTERVAL = 60

class RedditSource(pw.io.python.ConnectorSubject):
    def __init__(self):
        # No configuration parameters
```

#### New Approach:
```python
class RedditSource(pw.io.python.ConnectorSubject):
    def __init__(self, subreddits=None, post_limit=50, polling_interval=60):
        """Accept configuration from JSON"""
        if subreddits is None:
            subreddits = ["worldnews", "geopolitics", "news"]
        
        self.subreddits = "+".join(subreddits)  # Convert list to multi-subreddit format
        self.post_limit = post_limit
        self.polling_interval = polling_interval
```

**Benefits**:
- ✅ Configuration-driven (no code changes needed to add subreddits)
- ✅ Proper defaults fallback
- ✅ Uses instance variables instead of global constants
- ✅ Maintains backward compatibility

---

### 3. **Refactored `backend/connectors/telegram_src.py`**

#### Old Approach:
```python
# Hardcoded channel list
CHANNELS = ["intelslava", "insider_paper", "disclosetv", ...]

# Hardcoded bias tags
tags = {
    "intelslava": "Independent",
    "insider_paper": "Independent",
    ...
}

class TelegramSource(pw.io.python.ConnectorSubject):
    def __init__(self, api_id, api_hash, phone, polling_interval=60):
        # No channel configuration
```

#### New Approach:
```python
class TelegramSource(pw.io.python.ConnectorSubject):
    def __init__(self, api_id, api_hash, phone, channels=None, 
                 bias_tags=None, backfill_limit=20, polling_interval=60):
        """Accept channels and bias tags from JSON"""
        if channels is None:
            channels = ["intelslava", "insider_paper", "disclosetv"]
        
        self.channels = channels
        
        if bias_tags is None:
            bias_tags = {handle: "Independent" for handle in channels}
        
        self.bias_tags = bias_tags
        self.backfill_limit = backfill_limit
```

**Benefits**:
- ✅ Dynamic channel list from JSON config
- ✅ Bias tags properly mapped per channel
- ✅ Configurable backfill limit (historical messages)
- ✅ Maintains all functionality while being configuration-driven

---

### 4. **Updated `backend/data_registry.py`**

#### Telegram Source Initialization:
```python
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
    ...
)
print(f"✅ Enabled: Telegram ({len(channels)} channels)")
```

#### Reddit Source Initialization:
```python
t_reddit = pw.io.python.read(
    RedditSource(
        subreddits=reddit_config.get("subreddits", ["worldnews", "geopolitics"]),
        post_limit=reddit_config.get("post_limit", 50),
        polling_interval=reddit_config.get("polling_interval", 60)
    ),
    ...
)
print(f"✅ Enabled: Reddit ({len(reddit_config.get('subreddits', []))} subreddits)")
```

**Benefits**:
- ✅ Properly passes configuration from JSON to connectors
- ✅ Enhanced logging shows count of channels/subreddits
- ✅ Maintains error handling and fallback logic

---

## 📊 Data Sources Summary

### Total Sources: 54
- **RSS Feeds**: 18
- **Telegram Channels**: 25
- **Reddit Subreddits**: 10
- **News API**: 1 (GNews)

### Coverage by Region:
- **Ukraine-Russia**: 8 Telegram channels + 2 RSS feeds
- **Middle East**: 4 Telegram channels + 2 RSS feeds
- **Global OSINT**: 13 Telegram channels + 3 RSS feeds
- **Defense & Military**: 2 RSS feeds
- **Western News**: 7 RSS feeds
- **Pro-Russia**: 2 RSS feeds + channels

### Bias Distribution:
- **Pro Ukraine**: 5 sources
- **Pro Russia**: 3 sources
- **Independent/OSINT**: 15+ sources
- **US/Western**: 7 sources
- **Middle East**: 4 sources
- **European**: 2 sources
- **Varied (Reddit)**: 10 subreddits

---

## 🔄 Configuration Format (JSON Schema)

```json
{
  "rss_feeds": [
    {
      "name": "Source Name",
      "url": "https://...",
      "bias": "Bias Tag",
      "enabled": true,
      "polling_interval": 300
    }
  ],
  "telegram_sources": [
    {
      "name": "Network Name",
      "channels": [
        {
          "handle": "channel_handle",
          "bias": "Bias Tag",
          "region": "Region"
        }
      ],
      "enabled": true,
      "mode": "streaming",
      "backfill_messages": 20
    }
  ],
  "reddit_sources": [
    {
      "name": "Source Name",
      "subreddits": ["sub1", "sub2"],
      "post_limit": 50,
      "bias": "Varied",
      "enabled": true,
      "polling_interval": 60
    }
  ],
  "config": {
    "version": "2.0",
    "last_updated": "2026-03-07T12:00:00Z",
    "auto_reload": true,
    "reload_interval": 300
  }
}
```

---

## ✅ Validation

All files validated with no compile errors:
- ✅ `backend/connectors/reddit_src.py`
- ✅ `backend/connectors/telegram_src.py`
- ✅ `backend/data_registry.py`
- ✅ `data/data_sources.json`

---

## 🚀 Next Steps

1. **Test the configuration**:
   ```bash
   uv run backend/main.py
   ```

2. **Verify sources are loaded**:
   - Check console output for "✅ Enabled: [Source Name]" messages
   - Should see count of channels/subreddits in logs

3. **Monitor data flow**:
   - RSS feeds should poll every 5 minutes
   - Reddit should poll every 60 seconds
   - Telegram should stream in real-time

4. **Add more sources**: Simply edit `data/data_sources.json` - no code changes needed!

---

## 📝 Notes

- **Duplicate Handling**: All duplicate sources have been removed
- **Uniform Format**: All sources follow the same JSON structure pattern
- **Hot-Reload**: Configuration supports hot-reload (300s check interval)
- **Bias Tags**: Properly assigned based on source analysis and regional perspectives
- **Backward Compatibility**: Default values ensure system works even with minimal config

---

**Last Updated**: March 7, 2026  
**Configuration Version**: 2.0
