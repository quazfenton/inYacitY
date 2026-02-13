#!/usr/bin/env python3
"""
Master runner for all scrapers
Uses centralized config.json for modularity and easy configuration
Integrated with database sync based on sync mode configuration
"""

import asyncio
import json
import os
import hashlib
from datetime import datetime
from typing import List, Dict
from config_loader import get_config

# Import working scrapers with correct module names
from eventbrite_scraper import scrape_eventbrite
from meetup_scraper import scrape_meetup
from luma_scraper import scrape_luma
from dice_scraper import scrape_dice
from residad_scraper import scrape_ra
from posh_vip import scrape_posh_vip

BASE_DIR = os.path.dirname(__file__)
ALL_EVENTS_PATH = os.path.join(BASE_DIR, 'all_events.json')
SCRAPER_TRACKER_PATH = os.path.join(BASE_DIR, 'scraper_tracker.json')


class ScraperDeduplicationTracker:
    """Track scraped events locally to avoid re-scraping duplicates"""
    
    def __init__(self, tracker_file: str = SCRAPER_TRACKER_PATH):
        self.tracker_file = tracker_file
        self.data = {'events': {}, 'last_updated': None}
        self._load_tracker()
    
    def _load_tracker(self):
        """Load tracker from file"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = {'events': {}, 'last_updated': None}
    
    def _save_tracker(self):
        """Save tracker to file"""
        self.data['last_updated'] = datetime.now().isoformat()
        with open(self.tracker_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def _generate_hash(self, event: Dict) -> str:
        """Generate unique hash for event"""
        import hashlib
        key_parts = [
            event.get('title', '').lower().strip(),
            event.get('date', ''),
            event.get('location', '').lower().strip(),
            event.get('city', '').lower().strip()
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def is_tracked(self, event: Dict) -> bool:
        """Check if event has been tracked (O(1) lookup)"""
        event_hash = self._generate_hash(event)
        return event_hash in self.data['events']
    
    def add_events(self, events: List[Dict]):
        """Add events to tracker"""
        for event in events:
            event_hash = self._generate_hash(event)
            self.data['events'][event_hash] = {
                'title': event.get('title', ''),
                'date': event.get('date', ''),
                'city': event.get('city', ''),
                'tracked_at': datetime.now().isoformat()
            }
        self._save_tracker()
    
    def remove_synced_events(self, events: List[Dict]):
        """Remove successfully synced events from tracker (call after db sync)"""
        removed = 0
        for event in events:
            event_hash = self._generate_hash(event)
            if event_hash in self.data['events']:
                del self.data['events'][event_hash]
                removed += 1
        if removed > 0:
            self._save_tracker()
        return removed
    
    def remove_past_events(self, days: int = 30):
        """Remove events older than specified days"""
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        hashes_to_remove = []
        for event_hash, event_data in self.data['events'].items():
            if event_data.get('date', '2099-12-31') < cutoff_date:
                hashes_to_remove.append(event_hash)
        
        for event_hash in hashes_to_remove:
            del self.data['events'][event_hash]
        
        if hashes_to_remove:
            self._save_tracker()
        
        return len(hashes_to_remove)
    
    def get_stats(self) -> Dict:
        """Get tracker statistics"""
        return {
            'total_tracked': len(self.data['events']),
            'last_updated': self.data['last_updated']
        }


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
    
    # Initialize deduplication tracker
    tracker = ScraperDeduplicationTracker()
    print(f"[Tracker] {tracker.get_stats()['total_tracked']} events tracked from previous runs")

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
        for file_name in [
            'eventbrite_events.json',
            'meetup_events.json',
            'luma_events.json',
            'dice_events.json',
            'ra_events.json'
        ]:
            all_events.extend(load_city_events_from_file(os.path.join(BASE_DIR, file_name), location))

    # ===== DEDUPLICATION WITH TRACKER =====
    print(f"\n[DEDUP] Checking against local tracker...")
    print("-" * 70)
    
    # Ensure city is present
    for event in all_events:
        if not event.get('city'):
            event['city'] = location
    
    # Filter out already-tracked events (O(n) with hash set lookup)
    new_events = []
    skipped_count = 0
    for event in all_events:
        if tracker.is_tracked(event):
            skipped_count += 1
        else:
            new_events.append(event)
    
    if skipped_count > 0:
        print(f"[Tracker] Skipped {skipped_count} previously scraped events")
    
    # Remove duplicates by link (within this run)
    seen_links = {}
    unique_events = []
    for event in new_events:
        link = event.get('link', '')
        if link:
            if link not in seen_links:
                seen_links[link] = True
                unique_events.append(event)
        else:
            unique_events.append(event)
    
    # Add new unique events to tracker
    if unique_events:
        tracker.add_events(unique_events)
        print(f"[Tracker] Added {len(unique_events)} new events to tracker")

    # ===== MERGE AND SAVE =====
    print(f"\n[MERGE] Merging results...")
    print("-" * 70)

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
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Could not load existing events file: {e}")

        out_data['cities'][location] = {
            'events': unique_events,
            'total': len(unique_events),
            'last_updated': datetime.now().isoformat(),
            'sources': scraper_results
        }

        with open(ALL_EVENTS_PATH, 'w') as f:
            json.dump(out_data, f, indent=2, default=str)

        print(f"✓ Saved {len(unique_events)} merged events to {ALL_EVENTS_PATH}")

    # Copy to frontend public folder (merge cities properly)
    frontend_cache_target = os.path.join(BASE_DIR, '..', 'fronto', 'public', 'all_events.json')
    if os.path.exists(os.path.dirname(frontend_cache_target)):
        try:
            # Load existing frontend cache if it exists
            merged_data = {'cities': {}, 'last_updated': datetime.now().isoformat()}
            
            if os.path.exists(frontend_cache_target):
                try:
                    with open(frontend_cache_target, 'r') as f:
                        existing_frontend = json.load(f)
                        if isinstance(existing_frontend, dict) and existing_frontend.get('cities'):
                            merged_data['cities'] = existing_frontend['cities'].copy()
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Warning: Could not load existing frontend cache: {e}")
            
            # Merge in the new location data
            if location not in merged_data['cities'] or unique_events:
                merged_data['cities'][location] = {
                    'events': unique_events,
                    'total': len(unique_events),
                    'last_updated': datetime.now().isoformat(),
                    'sources': scraper_results
                }
            
            with open(frontend_cache_target, 'w') as f:
                json.dump(merged_data, f, indent=2, default=str)
            print("✓ Updated frontend cache at fronto/public/all_events.json")
        except Exception as e:
            print(f"Warning: Could not update frontend cache: {e}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_scraped = sum(scraper_results.values())
    print(f"Total events scraped: {total_scraped}")
    print(f"Unique events after dedup: {len(unique_events)}")
    duplicates_removed = max(0, total_scraped - len(unique_events))
    print(f"Duplicates removed: {duplicates_removed}")

    print("\nBy source:")
    for source, count in scraper_results.items():
        print(f"  {source}: {count}")

    print("\n" + "=" * 70)

    return unique_events, tracker


async def main():
    """Main entry point"""
    try:
        events, tracker = await run_all_scrapers()
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
            
            # Clean synced events from tracker if sync was successful
            if sync_result['success'] and sync_result['events_synced'] > 0:
                print("\n[Tracker] Cleaning synced events from local tracker...")
                # Load events that were synced and remove them from tracker
                if os.path.exists(ALL_EVENTS_PATH):
                    try:
                        with open(ALL_EVENTS_PATH, 'r') as f:
                            synced_data = json.load(f)
                            all_synced_events = []
                            if isinstance(synced_data, dict) and synced_data.get('cities'):
                                for city_data in synced_data['cities'].values():
                                    all_synced_events.extend(city_data.get('events', []))
                            else:
                                all_synced_events = synced_data.get('events', [])
                            
                            removed = tracker.remove_synced_events(all_synced_events)
                            print(f"[Tracker] Removed {removed} synced events from tracker")
                    except Exception as e:
                        print(f"[Tracker] Warning: Could not clean tracker: {e}")
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
