#!/usr/bin/env python3
"""Scrape Eventbrite for all cities with Firecrawl-only mode."""
import sys, json, asyncio, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scraper'))
os.environ['SKIP_PLAYWRIGHT'] = '1'

from eventbrite_scraper import scrape_eventbrite
from config_loader import get_config

config = get_config()
locations = config.get('SUPPORTED_LOCATIONS', [])

async def scrape_city(city: str, sem: asyncio.Semaphore) -> dict:
    async with sem:
        print(f"\n[{city}] Starting...")
        try:
            events = await scrape_eventbrite(location=city, max_pages=2)
            print(f"[{city}] Done: {len(events)} events")
            return {city: len(events)}
        except Exception as e:
            print(f"[{city}] Error: {e}")
            return {city: 0}

async def main():
    sem = asyncio.Semaphore(5)  # 5 concurrent
    tasks = [scrape_city(c, sem) for c in locations]
    results = await asyncio.gather(*tasks)
    total = 0
    print("\n" + "=" * 60)
    print("RESULTS:")
    for r in results:
        for city, count in r.items():
            print(f"  {city}: {count} events")
            total += count
    print(f"  TOTAL: {total} events")

asyncio.run(main())