# CFR Global Conflict Tracker - Scraping Guide

## Overview

The Global Conflict Tracker from the Center for Preventive Action (CPA) is an interactive guide to ongoing conflicts around the world, displaying nearly 30 conflicts with detailed information.

This guide shows you how to extract, parse, and store this data programmatically.

---

## 📊 Data Available

Each conflict entry includes:
- **Conflict Name**: Title (e.g., "War in Ukraine")
- **Region**: Geographic region
- **Conflict Type**: Category (Civil War, Interstate, Terrorism, etc.)
- **Impact on US**: Critical / Significant / Limited
- **Conflict Status**: Worsening / Unchanging / Improving
- **Countries Affected**: List of involved nations

---

## 🚀 Quick Start

### Installation
```bash
pip install requests beautifulsoup4
```

### Basic Usage
```python
from cfr_conflict_scraper import CFRConflictScraper

# Initialize scraper
scraper = CFRConflictScraper()

# Run full update (scrapes website, saves to SQLite)
scraper.run_full_update()

# Get all conflicts
all_conflicts = scraper.get_all_conflicts()
for conflict in all_conflicts:
    print(f"{conflict['name']}: {conflict['conflict_status']}")

# Export to JSON
scraper.export_json('conflicts.json')
```

---

## 📖 How It Works

### Step 1: Fetch Main Page
```python
scraper = CFRConflictScraper()
conflicts = scraper.fetch_main_page()
# Returns list of ~30 conflicts with basic info
```

**Output:**
```python
[
  {
    'name': 'War in Ukraine',
    'region': 'Europe and Eurasia',
    'conflict_type': 'Interstate',
    'impact_on_us': 'Critical',
    'conflict_status': 'Unchanging',
    'countries_affected': 'RU, UA',
    'url': 'https://www.cfr.org/global-conflict-tracker/conflict/conflict-ukraine',
    'fetched_date': '2026-03-07T10:30:45.123456'
  },
  ...
]
```

### Step 2: Save to Database
```python
scraper.save_conflicts(conflicts)
# Stores in SQLite3 database
# Auto-deduplicates by conflict name
# Updates existing entries
```

### Step 3: Query Database
```python
# By status
worsening = scraper.get_conflicts_by_status('Worsening')

# By impact
critical = scraper.get_conflicts_by_impact('Critical')

# By region
asia = scraper.get_conflicts_by_region('Asia')

# All conflicts
all_conflicts = scraper.get_all_conflicts()
```

### Step 4: Export Data
```python
scraper.export_json('cfr_conflicts.json')
# Exports all conflicts with statistics to JSON
```

---

## 🔍 Query Examples

### Get Critical Conflicts
```python
critical_conflicts = scraper.get_conflicts_by_impact('Critical')
print(f"Found {len(critical_conflicts)} critical conflicts:")
for conflict in critical_conflicts:
    print(f"  - {conflict['name']}")
```

**Output:**
```
Found 6 critical conflicts:
  - War in Ukraine
  - Confrontation Over Taiwan
  - Iran's War With Israel and the United States
  - U.S. Confrontation With Venezuela
  - North Korea Crisis
  - Territorial Disputes in the South China Sea
```

### Get Worsening Conflicts
```python
worsening = scraper.get_conflicts_by_status('Worsening')
for conflict in worsening:
    print(f"{conflict['name']} ({conflict['impact_on_us']})")
```

### Get Region-Specific Conflicts
```python
# Middle East conflicts
me_conflicts = scraper.get_conflicts_by_region('Middle East')

# Asia conflicts
asia_conflicts = scraper.get_conflicts_by_region('Asia')

# Americas conflicts
americas_conflicts = scraper.get_conflicts_by_region('Americas')
```

### Get Statistics
```python
stats = scraper.get_statistics()

print(f"Total Conflicts: {stats['total']}")
print(f"By Status: {stats['by_status']}")
print(f"By Impact: {stats['by_impact']}")
print(f"By Region: {stats['by_region']}")
```

**Output:**
```
Total Conflicts: 28

By Status: 
  Worsening: 12
  Unchanging: 10
  Improving: 2

By Impact:
  Critical: 6
  Significant: 9
  Limited: 13

By Region:
  Middle East and North Africa: 8
  Sub-Saharan Africa: 6
  Asia: 7
  Americas: 3
  Europe and Eurasia: 2
```

---

## 📁 Database Schema

The scraper creates `cfr_conflicts.db` with two tables:

### Table 1: `conflicts`
```
id (PRIMARY KEY)
name (UNIQUE)
region
conflict_type
impact_on_us
conflict_status
countries_affected
url
description
fetched_date
last_updated
```

### Table 2: `conflict_details`
```
id (PRIMARY KEY)
conflict_name (FOREIGN KEY)
detail_title
detail_content
fetched_date
```

---

## 🔄 Scheduling Updates

### Cron Job (Linux/Mac)
Update every 12 hours:
```bash
crontab -e

# Add this line:
0 */12 * * * /usr/bin/python3 /path/to/cfr_conflict_scraper.py
```

### Python Scheduler
```python
import schedule
import time
from cfr_conflict_scraper import CFRConflictScraper

scraper = CFRConflictScraper()

def update_job():
    scraper.run_full_update()

# Run every 12 hours
schedule.every(12).hours.do(update_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Windows Task Scheduler
1. Create `.bat` file:
```batch
@echo off
cd C:\path\to\project
python cfr_conflict_scraper.py
```

2. Open Task Scheduler
3. Create Basic Task
4. Set trigger to "Daily" or "Weekly"
5. Set action to run `.bat` file

---

## 💾 Export Formats

### JSON Export
```python
scraper.export_json('conflicts.json')
```

**Output format:**
```json
{
  "timestamp": "2026-03-07T10:30:45.123456",
  "total_conflicts": 28,
  "conflicts": [
    {
      "id": 1,
      "name": "War in Ukraine",
      "region": "Europe and Eurasia",
      "conflict_type": "Interstate",
      "impact_on_us": "Critical",
      "conflict_status": "Unchanging",
      "countries_affected": "RU, UA",
      "url": "https://...",
      "description": "...",
      "fetched_date": "...",
      "last_updated": "..."
    }
  ],
  "statistics": {
    "total": 28,
    "by_status": {...},
    "by_impact": {...},
    "by_region": {...}
  }
}
```

### CSV Export
```python
import csv

conflicts = scraper.get_all_conflicts()

with open('conflicts.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=conflicts[0].keys())
    writer.writeheader()
    writer.writerows(conflicts)
```

### SQL/Database
Already stored in SQLite3 `cfr_conflicts.db`

---

## 🔗 Integration with Flashpoint

For your **Flashpoint** geopolitical intelligence platform:

```python
from cfr_conflict_scraper import CFRConflictScraper

class FlashpointCFRIntegration:
    def __init__(self):
        self.scraper = CFRConflictScraper()
    
    def get_critical_conflicts(self):
        """Get conflicts critical to US interests"""
        return self.scraper.get_conflicts_by_impact('Critical')
    
    def get_worsening_hotspots(self):
        """Get situations deteriorating"""
        return self.scraper.get_conflicts_by_status('Worsening')
    
    def get_region_overview(self, region):
        """Get conflicts in specific region"""
        return self.scraper.get_conflicts_by_region(region)
    
    def get_latest_snapshot(self):
        """Get current state of all conflicts"""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_conflicts': len(self.scraper.get_all_conflicts()),
            'critical': self.scraper.get_conflicts_by_impact('Critical'),
            'worsening': self.scraper.get_conflicts_by_status('Worsening'),
            'statistics': self.scraper.get_statistics()
        }

# Usage in Flashpoint
integration = FlashpointCFRIntegration()

# Daily intelligence briefing
briefing = integration.get_latest_snapshot()
print(briefing)
```

---

## ⚠️ Important Notes

### Rate Limiting
- CFR doesn't have a strict rate limit, but be respectful
- Adding `time.sleep(1)` between requests is recommended
- Only scrape when necessary (12-24 hour intervals)

### Data Freshness
- CFR updates their tracker regularly
- Update frequency: Every 12-24 hours
- Page structure is relatively stable

### Terms of Service
- ✅ Data scraping allowed (public data)
- ✅ For non-commercial use
- ✅ Attribution appreciated
- ⚠️ Don't republish without credit

### Alternative: RSS Feed
CFR also provides an RSS feed:
```
https://www.cfr.org/rss-feeds
```

---

## 🐛 Troubleshooting

### Issue: "No conflicts found"
**Solution:** Page structure may have changed. Update CSS selectors in script.

### Issue: "Connection timeout"
**Solution:** CFR servers busy. Retry with increased timeout:
```python
response = requests.get(url, headers=headers, timeout=30)
```

### Issue: "Database locked"
**Solution:** SQLite locked by another process. Close other connections or use different database.

### Issue: "BeautifulSoup not parsing correctly"
**Solution:** Try different parser:
```python
soup = BeautifulSoup(response.content, 'lxml')  # Requires: pip install lxml
```

---

## 📊 Dashboard Example

```python
scraper = CFRConflictScraper()
scraper.run_full_update()
scraper.print_dashboard()
```

**Output:**
```
================================================================================
🔥 CFR GLOBAL CONFLICT TRACKER DASHBOARD
================================================================================

📊 Total Conflicts: 28

📈 By Status:
   📉 Worsening         12 conflicts
   ➡️  Unchanging        10 conflicts
   📈 Improving          2 conflicts

⚠️  By Impact on US:
   🔴 Critical          6 conflicts
   🟡 Significant       9 conflicts
   🟢 Limited          13 conflicts

🌍 By Region:
   Middle East and North Africa    8 conflicts
   Sub-Saharan Africa              6 conflicts
   Asia                            7 conflicts
   Americas                        3 conflicts
   Europe and Eurasia              2 conflicts

================================================================================
```

---

## 📚 Additional Resources

- **CFR Global Conflict Tracker**: https://www.cfr.org/global-conflict-tracker
- **CFR Methodology**: https://www.cfr.org/global-conflict-tracker/methodology
- **Center for Preventive Action**: https://www.cfr.org/programs/center-preventive-action

---

**Last Updated:** March 7, 2026  
**Tested With:** Python 3.8+  
**Dependencies:** `requests`, `beautifulsoup4`
