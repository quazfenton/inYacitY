#!/usr/bin/env python3
"""
Master runner for all scrapers
"""

import asyncio
import json
import os
import argparse
from datetime import datetime
from typing import List, Dict

# Import working scrapers
from luma import scrape_luma
from dice_fm import scrape_dice_fm
from ra_co import scrape_ra_co
from eventbrite_fixed import scrape_eventbrite
from meetup_simple import scrape_meetup_simple


def _write_frontend_cache(payload: dict) -> None:
    frontend_public = os.path.join(os.path.dirname(__file__), '../fronto/public')
    os.makedirs(frontend_public, exist_ok=True)
    frontend_path = os.path.join(frontend_public, 'all_events.json')
    with open(frontend_path, 'w') as f:
        json.dump(payload, f, indent=2, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))


async def run_all_scrapers(location_override: str = None):
    """Run all scrapers and merge results"""
    
    print("=" * 70)
    print("EVENT SCRAPER - Eventbrite + Meetup + Luma + Dice.fm + RA.co")
    print("=" * 70)
    
    # Load configuration
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")
    
    location = location_override or config.get('LOCATION', 'ca--los-angeles')
    print(f"\nLocation: {location}")
    print("=" * 70)
    
    all_events = []
    
    # ===== EVENTBRITE =====
    print("\n[1/5] Scraping Eventbrite...")
    print("-" * 70)
    try:
        eventbrite_events = await scrape_eventbrite(location)
        all_events.extend(eventbrite_events)
        print(f"✓ Eventbrite: {len(eventbrite_events)} events")
    except Exception as e:
        print(f"✗ Eventbrite error: {e}")
    
    # ===== MEETUP =====
    print("\n[2/5] Scraping Meetup...")
    print("-" * 70)
    try:
        # Convert location format
        if '--' in location:
            parts = location.split('--')
            meetup_location = f"us--{parts[0]}--{parts[1]}"
        else:
            meetup_location = f"us--{location}"
        
        meetup_events = await scrape_meetup_simple(meetup_location)
        all_events.extend(meetup_events)
        print(f"✓ Meetup: {len(meetup_events)} events")
    except Exception as e:
        print(f"✗ Meetup error: {e}")
    
    # ===== LUMA =====
    print("\n[3/5] Scraping Luma...")
    print("-" * 70)
    try:
        # Convert location
        location_to_luma = {
            'dc--washington': 'dc', 'ny--new-york': 'nyc',
            'ca--los-angeles': 'la', 'ca--san-francisco': 'sf'
        }
        luma_city = location_to_luma.get(location, 'la')
        luma_events = await scrape_luma(luma_city)
        all_events.extend(luma_events)
        print(f"✓ Luma: {len(luma_events)} events")
    except Exception as e:
        print(f"✗ Luma error: {e}")
    
    # ===== DICE.FM =====
    print("\n[4/5] Scraping Dice.fm...")
    print("-" * 70)
    try:
        dice_events = await scrape_dice_fm(location)
        all_events.extend(dice_events)
        print(f"✓ Dice.fm: {len(dice_events)} events")
    except Exception as e:
        print(f"✗ Dice.fm error: {e}")
    
    # ===== RA.CO =====
    print("\n[5/5] Scraping RA.co...")
    print("-" * 70)
    try:
        ra_events = await scrape_ra_co(location)
        all_events.extend(ra_events)
        print(f"✓ RA.co: {len(ra_events)} events")
    except Exception as e:
        print(f"✗ RA.co error: {e}")
    
    # ===== MERGE AND SAVE =====
    print(f"\n[6/6] Merging results...")
    print("-" * 70)
    
    # Remove duplicates by link
    seen_links = {}
    for event in all_events:
        link = event.get('link', '')
        if link:
            seen_links[link] = event
    
    unique_events = list(seen_links.values())
    for event in unique_events:
        event.setdefault('city', location)
    
    # Sort by date
    try:
        unique_events.sort(key=lambda x: x.get('date', '2099-12-31'))
    except:
        pass
    
    # Save
    existing_by_city = {}
    if os.path.exists('all_events.json'):
        try:
            with open('all_events.json', 'r') as f:
                existing_data = json.load(f)
                existing_by_city = existing_data.get('events_by_city', {}) or {}
        except Exception:
            existing_by_city = {}

    existing_by_city[location] = unique_events
    merged_events = []
    for city_events in existing_by_city.values():
        merged_events.extend(city_events)

    payload = {
        'events': merged_events,
        'total': len(merged_events),
        'last_updated': datetime.now().isoformat(),
        'location': location,
        'events_by_city': existing_by_city
    }
    with open('all_events.json', 'w') as f:
        json.dump(payload, f, indent=2, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
    _write_frontend_cache(payload)
    
    print(f"✓ Merged {len(unique_events)} unique events")
    print(f"✓ Saved to all_events.json")
    
    # Summary
    print("\n" + "=" * 70)
    print("✓ COMPLETE!")
    print("=" * 70)
    
    # Count by source
    sources = {}
    for e in unique_events:
        src = e.get('source', 'Unknown')
        sources[src] = sources.get(src, 0) + 1
    
    print("\nSummary:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count} events")
    print(f"  Total: {len(unique_events)} events")
    
    return unique_events


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run scrapers (Firecrawl)")
    parser.add_argument("-c", "--city", dest="city", help="Override city code (e.g., ca--san-francisco)")
    args = parser.parse_args()
    asyncio.run(run_all_scrapers(location_override=args.city))
