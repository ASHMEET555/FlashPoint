# FlashPoint Data Sources

FlashPoint aggregates intelligence from **53 sources** across multiple platforms, providing comprehensive coverage of global geopolitical events.

---

## Overview

| Type | Count | Update Frequency |
|------|-------|-----------------|
| RSS Feeds | 18 | Every 5 minutes |
| Telegram Channels | 25 | Real-time streaming |
| Reddit Communities | 10 | Every 1 minute |
| News APIs | 1 (GNews) | Every 10 minutes |

**Total**: 53 active sources

---

## Configuration

All sources are configured in `data/data_sources.json`:

```json
{
  "telegram_channels": [ ... ],
  "reddit_subreddits": [ ... ],
  "rss_feeds": [ ... ],
  "news_api": { ... }
}
```

---

## Telegram Channels (25)

Real-time streaming via Telethon. Bias tags indicate source perspective.

### Eastern/State Media (RU/CN)
- `@rian_ru` - RIA Novosti (Russia)
- `@rt_russian` - RT (Russia Today)
- `@tass_agency` - TASS (Russia)
- `@mod_russia` - Russian Ministry of Defense
- `@cgtnofficial` - CGTN (China)
- `@globaltimesnews` - Global Times (China)

### Western/NATO
- `@ukrinform` - Ukrinform (Ukraine)
- `@uniannet` - UNIAN (Ukraine)
- `@bbcnews` - BBC News
- `@reuters` - Reuters
- `@ap` - Associated Press
- `@cnnbrk` - CNN Breaking News
- `@nytimes` - New York Times

### Neutral/Regional
- `@AlJazeera` - Al Jazeera English
- `@QudsNen` - Al Quds News
- `@IsraelHayom` - Israel Hayom
- `@MiddleEastEye` - Middle East Eye
- `@MEMRIReports` - MEMRI

### Defense/OSINT
- `@Osinttechnical` - OSINT Technical
- `@IntelCrab` - Intel Crab
- `@sentdefender` - Sentinel Defender
- `@warmonitors` - War Monitors
- `@militarylandnet` - Military Land
- `@CIGeography` - Clash Report

---

## Reddit Communities (10)

Polled via public JSON API (no authentication required).

### News & Analysis
- `r/worldnews` - Global news and discussion
- `r/geopolitics` - Geopolitical analysis
- `r/internationalnews` - International reporting
- `r/GlobalTalk` - Global issues

### Conflict Coverage
- `r/UkrainianConflict` - Ukraine war updates
- `r/ukraine` - Ukrainian perspective
- `r/syriancivilwar` - Middle East conflicts
- `r/YemeniCrisis` - Yemen coverage

### Intelligence
- `r/OSINT` - Open-source intelligence
- `r/intelligence` - Intelligence community

---

## RSS Feeds (18)

Parsed with `feedparser` library.

### Global News
- **Reuters World News** - `http://feeds.reuters.com/Reuters/worldNews`
- **BBC World** - `http://feeds.bbci.co.uk/news/world/rss.xml`
- **Al Jazeera** - `https://www.aljazeera.com/xml/rss/all.xml`
- **AP Top News** - `https://apnews.com/apf-topnews`
- **France24 World** - `https://www.france24.com/en/rss`

### Regional Focus
- **Haaretz (Israel)** - `https://www.haaretz.com/cmlink/1.628752`
- **Times of Israel** - `https://www.timesofisrael.com/feed/`
- **Arab News** - `https://www.arabnews.com/rss.xml`
- **South China Morning Post** - `https://www.scmp.com/rss/91/feed`

### Defense/Military
- **Defense News** - `https://www.defensenews.com/arc/outboundfeeds/rss/`
- **Jane's Defence** - `https://www.janes.com/feeds/defence-news`
- **Breaking Defense** - `https://breakingdefense.com/feed/`

### Analysis
- **Foreign Policy** - `https://foreignpolicy.com/feed/`
- **War on the Rocks** - `https://warontherocks.com/feed/`
- **The Diplomat** - `https://thediplomat.com/feed/`

### Conflicts
- **Syria Direct** - `https://syriadirect.org/feed/`
- **Yemen Data Project** - `https://www.yemendataproject.org/rss/`
- **Ukraine Crisis Media Center** - `https://uacrisis.org/en/feed/`

---

## News APIs (1)

### GNews API
- **Update Frequency**: Every 10 minutes
- **Query**: "geopolitics OR conflict OR war OR crisis"
- **Language**: English
- **Max Results**: 10 per fetch
- **API Key**: Required (free tier: 100 requests/day)

**Configuration in `.env`**:
```bash
GNEWS_API_KEY=your_key_here
```

---

## Bias Classification

Sources are tagged with bias indicators:

| Bias Tag | Description | Examples |
|----------|-------------|----------|
| `State-Media (RU)` | Russian state media | RT, TASS, RIA Novosti |
| `State-Media (CN)` | Chinese state media | CGTN, Global Times |
| `State-Media (UA)` | Ukrainian state media | Ukrinform, UNIAN |
| `Western/Global` | Western mainstream | BBC, Reuters, AP, NYT |
| `Neutral/Global` | International neutrality | Al Jazeera, France24 |
| `Regional` | Regional focus | Arab News, Haaretz, SCMP |
| `OSINT` | Open-source intelligence | OSINT Technical, Intel Crab |
| `Defense` | Military/defense focus | Defense News, Jane's |

---

## Adding New Sources

### Telegram Channel

1. Add to `data/data_sources.json`:
```json
{
  "username": "channel_name",
  "bias": "Neutral",
  "enabled": true
}
```

2. Restart workers: `./stop.sh && ./start.sh`

### Reddit Subreddit

1. Add to `data/data_sources.json`:
```json
"reddit_subreddits": ["new_subreddit"]
```

2. Restart workers

### RSS Feed

1. Add to `data/data_sources.json`:
```json
{
  "url": "https://example.com/feed.xml",
  "name": "Example News",
  "enabled": true
}
```

2. Restart workers

---

## Source Quality Metrics

### Coverage by Region

- **Europe** (Ukraine, Russia): 12 sources
- **Middle East** (Israel, Syria, Yemen): 8 sources
- **Asia-Pacific** (China, Taiwan): 4 sources
- **Global** (Multi-regional): 29 sources

### Update Frequency

- **Real-time** (< 1 minute): Telegram (25 sources)
- **Near real-time** (1-5 minutes): Reddit (10 sources)
- **Regular** (5-10 minutes): RSS (18 sources) + GNews (1)

### Language Coverage

- **English**: 53 sources (100%)
- **Russian** (via translation): 6 sources
- **Chinese** (via translation): 2 sources
- **Arabic** (via translation): 3 sources

---

## Deduplication

**Method**: SHA256 content hashing  
**Window**: 24 hours  
**Storage**: Redis with automatic expiration

This prevents:
- Duplicate processing of same content
- Cross-posting across sources
- Feed republishing same article

---

## Rate Limiting

### Telegram
- **Flood Wait**: Auto-handled by Telethon
- **Max Messages**: No hard limit (streaming)

### Reddit
- **User-Agent**: FlashPoint/2.0
- **Rate**: 1 request/minute (30 requests/hour)
- **429 Handling**: Exponential backoff

### RSS
- **Politeness Delay**: 5 seconds between feeds
- **User-Agent**: FlashPoint RSS Reader

### GNews API
- **Free Tier**: 100 requests/day
- **Schedule**: Every 10 minutes = 144 requests/day
- **Rate Limit Handling**: Skip on 429, retry next cycle

---

## Monitoring

View source statistics:

```sql
-- PostgreSQL query
SELECT source, COUNT(*) as event_count 
FROM events 
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY source 
ORDER BY event_count DESC;
```

Check worker logs:

```bash
# RSS worker
tail -f logs/celery-worker.log | grep rss_worker

# Telegram worker
tail -f logs/celery-worker.log | grep telegram_worker

# Reddit worker
tail -f logs/celery-worker.log | grep reddit_worker
```

---

## Troubleshooting

### Telegram Not Streaming

1. Check session file: `session_flashpoint.session`
2. Verify credentials in `.env`
3. Check logs: `grep telegram logs/celery-worker.log`
4. Possible flood wait - check Telethon errors

### Reddit 429 Errors

1. Reduce polling frequency in `celery_config.py`
2. Check User-Agent string
3. Verify no other Reddit scraping running

### RSS Feed Failures

1. Check feed URL is accessible
2. Verify SSL certificate validity
3. Check `feedparser` parsing errors in logs
4. Some feeds may be geo-blocked

### GNews API Quota

1. Check daily usage: `https://gnews.io/`
2. Reduce polling frequency if hitting limit
3. Consider upgrading plan or using alternative

---

## Source Reliability

### Verification Hierarchy

1. **Tier 1** (High confidence): Reuters, AP, BBC
2. **Tier 2** (Medium confidence): Regional news, verified Telegram
3. **Tier 3** (Low confidence): Reddit, unverified social media

### Cross-Referencing

FlashPoint encourages cross-referencing by:
- Showing source and bias tag on each event
- Bias meter comparing narratives
- Multiple sources per event in RAG context

---

*Last Updated: March 2026*  
*Total Active Sources: 53*
