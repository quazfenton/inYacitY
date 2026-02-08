#!/usr/bin/env python3
"""
Master runner for all scrapers
Uses centralized config.json for modularity and easy configuration
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict
from config_loader import get_config

# Import working scrapers with correct module names
from eventbrite_scraper import scrape_eventbrite
from meetup_scraper import scrape_meetup
from luma_scraper import scrape_luma
from dice_scraper import scrape_dice
from posh_vip import scrape_posh_vip


async def run_all_scrapers():
    """Run all scrapers and merge results"""
    
    print("=" * 70)
    print("EVENT SCRAPER - All Sources")
    print("=" * 70)
    
    # Load configuration using config loader
    config = get_config()
    location = config.get_location()
    
    print(f"\nLocation: {location}")
    print(f"Browser Settings: Headless={config.get('BROWSER.HEADLESS')}")
    print("=" * 70)
    
    all_events = []
    scraper_results = {}
    
    # ===== EVENTBRITE =====
    if config.is_scraper_enabled('EVENTBRITE'):
        print("\n[1/5] Scraping Eventbrite...")
        print("-" * 70)
        try:
            eventbrite_events = await scrape_eventbrite(location)
            all_events.extend(eventbrite_events)
            scraper_results['Eventbrite'] = len(eventbrite_events)
            print(f"✓ Eventbrite: {len(eventbrite_events)} events")
        except Exception as e:
            print(f"✗ Eventbrite error: {e}")
            scraper_results['Eventbrite'] = 0
    
    # ===== MEETUP =====
    if config.is_scraper_enabled('MEETUP'):
        print("\n[2/5] Scraping Meetup...")
        print("-" * 70)
        try:
            meetup_events = await scrape_meetup(location)
            all_events.extend(meetup_events)
            scraper_results['Meetup'] = len(meetup_events)
            print(f"✓ Meetup: {len(meetup_events)} events")
        except Exception as e:
            print(f"✗ Meetup error: {e}")
            scraper_results['Meetup'] = 0
    
    # ===== LUMA =====
    if config.is_scraper_enabled('LUMA'):
        print("\n[3/5] Scraping Luma...")
        print("-" * 70)
        try:
            luma_events = await scrape_luma(location)
            all_events.extend(luma_events)
            scraper_results['Luma'] = len(luma_events)
            print(f"✓ Luma: {len(luma_events)} events")
        except Exception as e:
            print(f"✗ Luma error: {e}")
            scraper_results['Luma'] = 0
    
    # ===== DICE.FM =====
    if config.is_scraper_enabled('DICE_FM'):
        print("\n[4/5] Scraping Dice.fm...")
        print("-" * 70)
        try:
            dice_events = await scrape_dice(location)
            all_events.extend(dice_events)
            scraper_results['Dice.fm'] = len(dice_events)
            print(f"✓ Dice.fm: {len(dice_events)} events")
        except Exception as e:
            print(f"✗ Dice.fm error: {e}")
            scraper_results['Dice.fm'] = 0
    
    # ===== RA.CO =====
    if config.is_scraper_enabled('RA_CO'):
        print("\n[5/5] Scraping RA.co...")
        print("-" * 70)
        try:
            ra_events = await scrape_dice(location)  # Using correct function
            all_events.extend(ra_events)
            scraper_results['RA.co'] = len(ra_events)
            print(f"✓ RA.co: {len(ra_events)} events")
        except Exception as e:
            print(f"✗ RA.co error: {e}")
            scraper_results['RA.co'] = 0
    
    # ===== MERGE AND SAVE =====
    print(f"\n[MERGE] Merging results...")
    print("-" * 70)
    
    # Remove duplicates by link
    seen_links = {}
    for event in all_events:
        link = event.get('link', '')
        if link:
            seen_links[link] = event
    
    unique_events = list(seen_links.values())
    
    # Sort by date
    try:
        unique_events.sort(key=lambda x: x.get('date', '2099-12-31'))
    except Exception as e:
        print(f"Warning: Could not sort events: {e}")
    
    # Save merged events
    output_settings = config.get_output_settings()
    
    if output_settings.get('MERGE_ALL', True):
        with open('all_events.json', 'w') as f:
            json.dump({
                'events': unique_events,
                'total': len(unique_events),
                'location': location,
                'timestamp': datetime.now().isoformat(),
                'sources': scraper_results
            }, f, indent=2, default=str)
        
        print(f"✓ Saved {len(unique_events)} merged events to all_events.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_scraped = sum(scraper_results.values())
    print(f"Total events scraped: {total_scraped}")
    print(f"Unique events after dedup: {len(unique_events)}")
    print(f"Duplicates removed: {total_scraped - len(unique_events)}")
    
    print("\nBy source:")
    for source, count in scraper_results.items():
        print(f"  {source}: {count}")
    
    print("\n" + "=" * 70)
    
    return unique_events


async def main():
    """Main entry point"""
    try:
        events = await run_all_scrapers()
        print(f"\n✓ Scraping completed successfully")
        return 0
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
