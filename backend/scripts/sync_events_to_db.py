#!/usr/bin/env python3
"""Load events from scraper cache files and save to the database directly."""
import sys, json, os, asyncio

# Set up paths
backend_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, '../scraper'))

# Force Firecrawl-only mode
os.environ['SKIP_PLAYWRIGHT'] = '1'

from database import save_events, init_db
from config import CONFIG, SUPPORTED_LOCATIONS

async def main():
    await init_db()
    
    scraper_dir = os.path.join(backend_dir, '../scraper')
    total_saved = 0
    total_updated = 0
    
    # Load from eventbrite_events.json (cities format)
    eb_path = os.path.join(scraper_dir, 'eventbrite_events.json')
    if os.path.exists(eb_path):
        with open(eb_path) as f:
            data = json.load(f)
        if 'cities' in data:
            for city_key, city_data in data['cities'].items():
                events = city_data.get('events', [])
                if events:
                    result = await save_events(events, city_key)
                    total_saved += result['saved']
                    total_updated += result['updated']
                    print(f"  {city_key}: {result['saved']} new, {result['updated']} updated ({len(events)} total)")
    
    # Also try loading from all_events.json if available
    all_path = os.path.join(scraper_dir, 'all_events.json')
    if os.path.exists(all_path):
        with open(all_path) as f:
            data = json.load(f)
        events = data.get('events', [])
        # Group by city
        by_city = {}
        for e in events:
            city = e.get('city', 'unknown')
            by_city.setdefault(city, []).append(e)
        for city_key, city_events in by_city.items():
            if city_key not in [k for k in _get_already_saved()]:
                result = await save_events(city_events, city_key)
                total_saved += result['saved']
                total_updated += result['updated']
                print(f"  {city_key} (from all_events): {result['saved']} new, {result['updated']} updated")
    
    print(f"\nTotal: {total_saved} new, {total_updated} updated")

if __name__ == '__main__':
    asyncio.run(main())
