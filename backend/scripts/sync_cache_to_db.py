#!/usr/bin/env python3
"""Load events from scraper cache files and save to the database."""
import sys, json, os, asyncio
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/scraper')

from database import save_events, init_db_async

async def main():
    await init_db_async()
    
    scraper_dir = '/app/scraper'
    total_saved = total_updated = 0
    
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
                    print(f'{city_key}: {result["saved"]} new, {result["updated"]} updated ({len(events)} total)')
    
    print(f'\nDB sync complete: {total_saved} new, {total_updated} updated')

if __name__ == '__main__':
    asyncio.run(main())
