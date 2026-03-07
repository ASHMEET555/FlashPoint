"""
CFR Global Conflict Tracker Scraper
Extracts conflict data from https://www.cfr.org/global-conflict-tracker
"""

import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import time

class CFRConflictScraper:
    """
    Scrapes CFR Global Conflict Tracker for conflict data.
    Updates every 6-24 hours (manually triggered or scheduled).
    """
    
    def __init__(self, db_path="./cfr_conflicts.db"):
        self.base_url = "https://www.cfr.org/global-conflict-tracker"
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                region TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                impact_on_us TEXT NOT NULL,
                conflict_status TEXT NOT NULL,
                countries_affected TEXT NOT NULL,
                url TEXT,
                description TEXT,
                fetched_date TEXT,
                last_updated TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conflict_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conflict_name TEXT NOT NULL,
                detail_title TEXT,
                detail_content TEXT,
                fetched_date TEXT,
                FOREIGN KEY(conflict_name) REFERENCES conflicts(name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def fetch_main_page(self) -> List[Dict]:
        """
        Fetch and parse the main conflict tracker page
        
        Returns:
            List of conflict dictionaries with basic info
        """
        
        print(f"\n📡 Fetching CFR Global Conflict Tracker...")
        print("=" * 70)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'
            }
            
            response = requests.get(self.base_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            conflicts = []
            
            # Find all conflict entries
            # Based on the page structure, conflicts are in h3/bullet list items
            conflict_items = soup.find_all('h3')
            
            for item in conflict_items:
                try:
                    # Extract conflict name
                    name = item.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                    
                    # Find parent container with details
                    parent = item.find_parent('div')
                    if not parent:
                        parent = item.find_parent('li')
                    
                    # Extract details from nearby elements
                    details_text = parent.get_text() if parent else ""
                    
                    conflict = {
                        'name': name,
                        'url': f"{self.base_url}/conflict/{self._slugify(name)}",
                        'region': self._extract_field(details_text, 'Region'),
                        'conflict_type': self._extract_field(details_text, 'Type of Conflict'),
                        'impact_on_us': self._extract_field(details_text, 'Impact on US Interests'),
                        'conflict_status': self._extract_field(details_text, 'Conflict Status'),
                        'countries_affected': self._extract_field(details_text, 'Countries Affected'),
                        'fetched_date': datetime.now().isoformat()
                    }
                    
                    conflicts.append(conflict)
                    print(f"✓ {name[:50]:50} | {conflict['region']}")
                
                except Exception as e:
                    print(f"⚠ Error parsing item: {str(e)[:50]}")
                    continue
            
            print("=" * 70)
            print(f"✅ Found {len(conflicts)} conflicts")
            return conflicts
        
        except Exception as e:
            print(f"❌ Error fetching page: {e}")
            return []
    
    def _extract_field(self, text: str, field_name: str) -> str:
        """Extract specific field value from text"""
        try:
            if field_name not in text:
                return "Unknown"
            
            start = text.find(field_name) + len(field_name)
            end = text.find('\n', start)
            
            if end == -1:
                end = len(text)
            
            value = text[start:end].strip().replace(':', '').strip()
            return value if value else "Unknown"
        except:
            return "Unknown"
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL slug"""
        return text.lower().replace(' ', '-').replace('/', '-')
    
    def fetch_conflict_details(self, conflict: Dict) -> Dict:
        """
        Fetch detailed information for a specific conflict
        
        Args:
            conflict: Conflict dict with URL
        
        Returns:
            Updated conflict dict with details
        """
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'
            }
            
            # Construct detail URL
            url = conflict['url']
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract description/content
            description_elem = soup.find('div', class_='description')
            if not description_elem:
                description_elem = soup.find('div', class_='content')
            
            conflict['description'] = description_elem.get_text(strip=True)[:500] if description_elem else "N/A"
            conflict['last_updated'] = datetime.now().isoformat()
            
            print(f"  ✓ Fetched details: {conflict['name'][:40]}")
            return conflict
        
        except Exception as e:
            print(f"  ⚠ Could not fetch details: {str(e)[:50]}")
            return conflict
    
    def save_conflicts(self, conflicts: List[Dict]) -> int:
        """
        Save conflicts to database
        
        Args:
            conflicts: List of conflict dicts
        
        Returns:
            Number of new conflicts added
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_count = 0
        updated_count = 0
        
        for conflict in conflicts:
            try:
                # Check if exists
                cursor.execute('SELECT id FROM conflicts WHERE name = ?', (conflict['name'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Update
                    cursor.execute('''
                        UPDATE conflicts 
                        SET region = ?, conflict_type = ?, impact_on_us = ?, 
                            conflict_status = ?, countries_affected = ?, last_updated = ?
                        WHERE name = ?
                    ''', (
                        conflict['region'],
                        conflict['conflict_type'],
                        conflict['impact_on_us'],
                        conflict['conflict_status'],
                        conflict['countries_affected'],
                        datetime.now().isoformat(),
                        conflict['name']
                    ))
                    updated_count += 1
                else:
                    # Insert
                    cursor.execute('''
                        INSERT INTO conflicts 
                        (name, region, conflict_type, impact_on_us, conflict_status, 
                         countries_affected, url, description, fetched_date, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        conflict['name'],
                        conflict['region'],
                        conflict['conflict_type'],
                        conflict['impact_on_us'],
                        conflict['conflict_status'],
                        conflict['countries_affected'],
                        conflict.get('url', ''),
                        conflict.get('description', ''),
                        conflict['fetched_date'],
                        datetime.now().isoformat()
                    ))
                    new_count += 1
            
            except Exception as e:
                print(f"⚠ Error saving {conflict['name']}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Saved: {new_count} new, {updated_count} updated")
        return new_count
    
    def get_conflicts_by_status(self, status: str) -> List[Dict]:
        """
        Query conflicts by status
        
        Args:
            status: 'Worsening', 'Unchanging', or 'Improving'
        
        Returns:
            List of matching conflicts
        """
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conflicts WHERE conflict_status = ? ORDER BY name', (status,))
        conflicts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return conflicts
    
    def get_conflicts_by_impact(self, impact: str) -> List[Dict]:
        """
        Query conflicts by US impact
        
        Args:
            impact: 'Critical', 'Significant', or 'Limited'
        
        Returns:
            List of matching conflicts
        """
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conflicts WHERE impact_on_us = ? ORDER BY name', (impact,))
        conflicts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return conflicts
    
    def get_conflicts_by_region(self, region: str) -> List[Dict]:
        """
        Query conflicts by region
        
        Args:
            region: Region name
        
        Returns:
            List of matching conflicts
        """
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conflicts WHERE region LIKE ? ORDER BY name', (f'%{region}%',))
        conflicts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return conflicts
    
    def get_all_conflicts(self) -> List[Dict]:
        """Get all conflicts from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conflicts ORDER BY impact_on_us DESC, name')
        conflicts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return conflicts
    
    def get_statistics(self) -> Dict:
        """Get conflict statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total conflicts
        cursor.execute('SELECT COUNT(*) FROM conflicts')
        total = cursor.fetchone()[0]
        
        # By status
        cursor.execute('SELECT conflict_status, COUNT(*) FROM conflicts GROUP BY conflict_status')
        by_status = dict(cursor.fetchall())
        
        # By impact
        cursor.execute('SELECT impact_on_us, COUNT(*) FROM conflicts GROUP BY impact_on_us')
        by_impact = dict(cursor.fetchall())
        
        # By region
        cursor.execute('SELECT region, COUNT(*) FROM conflicts GROUP BY region')
        by_region = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total': total,
            'by_status': by_status,
            'by_impact': by_impact,
            'by_region': by_region
        }
    
    def print_dashboard(self):
        """Print formatted dashboard"""
        stats = self.get_statistics()
        
        print("\n" + "=" * 80)
        print("🔥 CFR GLOBAL CONFLICT TRACKER DASHBOARD")
        print("=" * 80)
        
        print(f"\n📊 Total Conflicts: {stats['total']}")
        
        print(f"\n📈 By Status:")
        for status, count in sorted(stats['by_status'].items()):
            emoji = "📉" if status == "Worsening" else "➡️" if status == "Unchanging" else "📈"
            print(f"   {emoji} {status:15} {count:3} conflicts")
        
        print(f"\n⚠️  By Impact on US:")
        for impact, count in sorted(stats['by_impact'].items(), 
                                   key=lambda x: {'Critical': 0, 'Significant': 1, 'Limited': 2}.get(x[0], 3)):
            emoji = "🔴" if impact == "Critical" else "🟡" if impact == "Significant" else "🟢"
            print(f"   {emoji} {impact:15} {count:3} conflicts")
        
        print(f"\n🌍 By Region:")
        for region, count in sorted(stats['by_region'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {region:35} {count:3} conflicts")
        
        print("\n" + "=" * 80 + "\n")
    
    def export_json(self, filename: str = "cfr_conflicts.json"):
        """Export all conflicts to JSON"""
        conflicts = self.get_all_conflicts()
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'total_conflicts': len(conflicts),
            'conflicts': conflicts,
            'statistics': self.get_statistics()
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"✅ Exported {len(conflicts)} conflicts to {filename}")
    
    def run_full_update(self, fetch_details: bool = False):
        """
        Run complete update cycle
        
        Args:
            fetch_details: Whether to fetch individual conflict pages
        """
        
        print("\n🔄 Starting CFR Conflict Tracker Update...")
        
        # Fetch main page
        conflicts = self.fetch_main_page()
        
        if not conflicts:
            print("❌ No conflicts found!")
            return
        
        # Optionally fetch details for each conflict
        if fetch_details:
            print("\n📖 Fetching detailed information...")
            print("=" * 70)
            for i, conflict in enumerate(conflicts):
                print(f"({i+1}/{len(conflicts)})", end=" ")
                conflict = self.fetch_conflict_details(conflict)
                time.sleep(1)  # Be respectful to the server
        
        # Save to database
        print("\n💾 Saving to database...")
        self.save_conflicts(conflicts)
        
        # Display dashboard
        self.print_dashboard()
        
        # Export JSON
        self.export_json()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    scraper = CFRConflictScraper()
    
    # Run full update (fetch main page only, basic details)
    scraper.run_full_update(fetch_details=False)
    
    # Show dashboard
    scraper.print_dashboard()
    
    # Query examples
    print("\n" + "=" * 80)
    print("🔴 CRITICAL IMPACT ON US (Highest Priority)")
    print("=" * 80)
    critical = scraper.get_conflicts_by_impact('Critical')
    for conflict in critical:
        print(f"\n{conflict['name']}")
        print(f"  Region: {conflict['region']}")
        print(f"  Status: {conflict['conflict_status']}")
        print(f"  Countries: {conflict['countries_affected']}")
    
    # Worsening conflicts
    print("\n" + "=" * 80)
    print("📉 WORSENING CONFLICTS (Watch List)")
    print("=" * 80)
    worsening = scraper.get_conflicts_by_status('Worsening')
    for conflict in worsening:
        print(f"  • {conflict['name']:45} ({conflict['region']})")
    
    # By region
    print("\n" + "=" * 80)
    print("🌍 MIDDLE EAST CONFLICTS")
    print("=" * 80)
    middle_east = scraper.get_conflicts_by_region('Middle East')
    for conflict in middle_east:
        print(f"  • {conflict['name']:50} - {conflict['conflict_status']}")
    
    print("\n" + "=" * 80)
    print("✅ Update complete!")
    print("=" * 80)
