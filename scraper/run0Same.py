#!/usr/bin/env python3
"""
Master runner for all scrapers
Uses centralized config.json for modularity and easy configuration
Integrated with database sync based on sync mode configuration
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
from ra_scraper import scrape_ra
from posh_vip import scrape_posh_vip

BASE_DIR = os.path.dirname(__file__)
ALL_EVENTS_PATH = os.path.join(BASE_DIR, 'all_events.json')


def load_city_events_from_file(path: str, city: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get('cities'):
            return data['cities'].get(city, {}).get('events', [])
        return data.get('events', [])
    except Exception:
        return []


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
            ra_events = await scrape_ra(location)
            all_events.extend(ra_events)
            scraper_results['RA.co'] = len(ra_events)
            print(f"✓ RA.co: {len(ra_events)} events")
        except Exception as e:
            print(f"✗ RA.co error: {e}")
            scraper_results['RA.co'] = 0

    # If no events returned, load from per-scraper files as fallback
    if not all_events:
        print("No events returned from scrapers, loading from cached JSON outputs...")
        fallback_files = [
            ('eventbrite_events.json', 'Eventbrite'),
            ('meetup_events.json', 'Meetup'),
            ('luma_events.json', 'Luma'),
            ('dice_events.json', 'Dice.fm'),
            ('ra_events.json', 'RA.co')
        ]
        for file_name, scraper_name in fallback_files:
            fallback_events = load_city_events_from_file(os.path.join(BASE_DIR, file_name), location)
            all_events.extend(fallback_events)
            scraper_results[scraper_name] = len(fallback_events)

    # ===== MERGE AND SAVE =====
    print(f"\n[MERGE] Merging results...")
    print("-" * 70)

    # Ensure city is present
    for event in all_events:
        if not event.get('city'):
            event['city'] = location

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

    # Save merged events (city-scoped)
    output_settings = config.get_output_settings()

    if output_settings.get('MERGE_ALL', True):
        out_data = {'cities': {}, 'last_updated': datetime.now().isoformat()}
        if os.path.exists(ALL_EVENTS_PATH):
            try:
                with open(ALL_EVENTS_PATH, 'r') as f:
                    existing = json.load(f)
                    if isinstance(existing, dict) and existing.get('cities'):
                        out_data['cities'] = existing['cities']
            except:
                pass

        out_data['cities'][location] = {
            'events': unique_events,
            'total': len(unique_events),
            'last_updated': datetime.now().isoformat(),
            'sources': scraper_results
        }

        with open(ALL_EVENTS_PATH, 'w') as f:
            json.dump(out_data, f, indent=2, default=str)

        print(f"✓ Saved {len(unique_events)} merged events to {ALL_EVENTS_PATH}")

    # Optional cache copy for frontend
    cache_target = os.path.join(BASE_DIR, '..', 'fronto', 'public', 'cache', 'all_events.json')
    if os.path.exists(os.path.dirname(cache_target)):
        try:
            with open(ALL_EVENTS_PATH, 'r') as src, open(cache_target, 'w') as dst:
                dst.write(src.read())
            print("✓ Updated frontend cache at fronto/public/cache/all_events.json")
        except Exception:
            pass

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

        # ===== DATABASE SYNC INTEGRATION =====
        config = get_config()
        sync_mode = config.get('DATABASE.SYNC_MODE', 0)

        # Track runs using a file-based counter
        run_counter_file = os.path.join(BASE_DIR, "scraper_run_counter.txt")
        try:
            with open(run_counter_file, 'r') as f:
                run_count = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            run_count = 1

        # Determine if we should sync
        should_sync = False
        if sync_mode == 0:
            should_sync = False
        elif 1 <= sync_mode <= 4:
            # Batch mode: sync every Nth run
            should_sync = (run_count % sync_mode == 0)
        elif sync_mode >= 5:
            # Always sync
            should_sync = True

        # Perform sync if needed
        if should_sync:
            print("\n" + "=" * 70)
            print("DATABASE SYNC")
            print("=" * 70)

            from db_sync import DatabaseSyncManager
            manager = DatabaseSyncManager()
            sync_result = await manager.sync_events(events_file=ALL_EVENTS_PATH)

            print(f"\n✓ Sync Status: {'SUCCESS' if sync_result['success'] else 'FAILED'}")
            print(f"  - Events synced: {sync_result['events_synced']}")
            print(f"  - Duplicates removed: {sync_result['new_duplicates_removed']}")
            print(f"  - Past events cleaned: {sync_result['past_events_removed']}")

            if sync_result['errors']:
                print("  - Errors encountered:")
                for error in sync_result['errors']:
                    print(f"    • {error}")
        else:
            sync_interval = sync_mode if sync_mode > 0 else "never"
            print(f"\n[SYNC] Skipped (run {run_count}, interval: every {sync_interval} run{'s' if sync_mode != 1 else ''})")

        # Increment and save run counter
        with open(run_counter_file, 'w') as f:
            f.write(str(run_count + 1))

        return 0
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
