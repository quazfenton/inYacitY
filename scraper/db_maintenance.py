#!/usr/bin/env python3
"""
Database Maintenance & Repair Tool

Handles:
- Update existing database events by hash/link after local patching
- Remove corrupted/recently added events from database
- Sync specific events or batches
- Database cleanup and repair operations
- Compare local vs database state

Usage:
    python db_maintenance.py --update-by-hash <hash>
    python db_maintenance.py --update-by-link <link>
    python db_maintenance.py --remove-recent --hours 24
    python db_maintenance.py --sync-patched
    python db_maintenance.py --compare-local-db
    python db_maintenance.py --remove-missing-from-local
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_sync import DatabaseSyncManager, EventDataValidator
from config_loader import get_config


class DatabaseMaintenanceTool:
    """Tool for maintaining and repairing database events"""
    
    def __init__(self, events_file: str = "all_events.json"):
        self.events_file = events_file
        self.config = get_config()
        self.sync_manager = DatabaseSyncManager()
        self.local_events = []
        self._load_local_events()
    
    def _load_local_events(self):
        """Load events from local file"""
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract events from nested structure
                self.local_events = data.get('events', [])
                if not self.local_events and isinstance(data, dict) and data.get('cities'):
                    for city_id, city_data in data['cities'].items():
                        if isinstance(city_data, dict) and 'events' in city_data:
                            for event in city_data['events']:
                                event['city'] = city_id
                            self.local_events.extend(city_data['events'])
                
                print(f"[OK] Loaded {len(self.local_events)} local events")
            except Exception as e:
                print(f"[ERROR] Failed to load local events: {e}")
                self.local_events = []
        else:
            print(f"[WARN] Local events file not found: {self.events_file}")
            self.local_events = []
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            from supabase import create_client
            supabase_url = os.environ.get('SUPABASE_URL') or self.config.get('SUPABASE_URL')
            supabase_key = os.environ.get('SUPABASE_KEY') or self.config.get('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                print("[ERROR] Supabase credentials not configured")
                return None
            
            return create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"[ERROR] Failed to connect to database: {e}")
            return None
    
    def _generate_event_hash(self, event: Dict) -> str:
        """Generate consistent hash for event"""
        import hashlib
        key_parts = [
            event.get('title', '').lower().strip(),
            event.get('date', ''),
            event.get('location', '').lower().strip(),
            event.get('city', '').lower().strip(),
            event.get('source', '')
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def update_event_by_hash(self, event_hash: str, updated_fields: Dict) -> bool:
        """Update a specific event in database by its hash"""
        client = self._get_db_connection()
        if not client:
            return False
        
        try:
            # Find event by hash
            result = client.table('events').select('*').eq('event_hash', event_hash).execute()
            
            if not result.data:
                print(f"[WARN] No event found with hash: {event_hash}")
                return False
            
            # Update the event
            update_result = client.table('events').update(updated_fields).eq('event_hash', event_hash).execute()
            
            if update_result.data:
                print(f"[OK] Updated event with hash: {event_hash}")
                print(f"     Fields updated: {list(updated_fields.keys())}")
                return True
            else:
                print(f"[WARN] Update returned no data for hash: {event_hash}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to update event by hash: {e}")
            return False
    
    async def update_event_by_link(self, link: str, updated_fields: Dict) -> bool:
        """Update a specific event in database by its link"""
        client = self._get_db_connection()
        if not client:
            return False
        
        try:
            # Find event by link
            result = client.table('events').select('*').eq('link', link).execute()
            
            if not result.data:
                print(f"[WARN] No event found with link: {link}")
                return False
            
            # Update the event
            update_result = client.table('events').update(updated_fields).eq('link', link).execute()
            
            if update_result.data:
                print(f"[OK] Updated event with link: {link[:50]}...")
                print(f"     Fields updated: {list(updated_fields.keys())}")
                return True
            else:
                print(f"[WARN] Update returned no data for link")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to update event by link: {e}")
            return False
    
    async def update_all_from_local(self, dry_run: bool = False) -> Tuple[int, int]:
        """Update all database events that exist in local file with local data"""
        client = self._get_db_connection()
        if not client:
            return 0, 0
        
        updated_count = 0
        error_count = 0
        
        print(f"\n[SYNC PATCHED EVENTS TO DATABASE]")
        print(f"Local events: {len(self.local_events)}")
        
        for idx, local_event in enumerate(self.local_events):
            try:
                # Generate hash for lookup
                event_hash = local_event.get('event_hash') or self._generate_event_hash(local_event)
                
                # Check if exists in database
                result = client.table('events').select('event_hash').eq('event_hash', event_hash).execute()
                
                if result.data:
                    # Event exists - update it with local data
                    update_data = {
                        'title': local_event.get('title'),
                        'date': local_event.get('date'),
                        'time': local_event.get('time', 'TBA'),
                        'location': local_event.get('location'),
                        'description': local_event.get('description', ''),
                        'price': local_event.get('price', 0),
                        'price_tier': local_event.get('price_tier', 0),
                        'category': local_event.get('category', 'Other'),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if not dry_run:
                        client.table('events').update(update_data).eq('event_hash', event_hash).execute()
                    
                    updated_count += 1
                    
                    if (idx + 1) % 10 == 0:
                        print(f"  Progress: {idx + 1}/{len(self.local_events)} events processed...")
                
            except Exception as e:
                error_count += 1
                print(f"  [ERROR] Event {idx}: {e}")
        
        print(f"\nResults:")
        print(f"  Updated: {updated_count}")
        print(f"  Errors: {error_count}")
        
        if dry_run:
            print("  [DRY-RUN] No changes were made")
        
        return updated_count, error_count
    
    async def remove_recent_events(self, hours: int = 24, dry_run: bool = False) -> int:
        """Remove events added within the last N hours"""
        client = self._get_db_connection()
        if not client:
            return 0
        
        try:
            # Calculate cutoff time
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Find recent events
            result = client.table('events').select('event_hash, title, created_at').gte('created_at', cutoff_time).execute()
            
            if not result.data:
                print(f"[OK] No events found from last {hours} hours")
                return 0
            
            events_to_remove = result.data
            print(f"\n[REMOVE RECENT EVENTS]")
            print(f"Found {len(events_to_remove)} events from last {hours} hours:")
            
            for event in events_to_remove[:5]:
                print(f"  - {event.get('title', 'Untitled')} ({event.get('created_at', 'unknown')})")
            
            if len(events_to_remove) > 5:
                print(f"  ... and {len(events_to_remove) - 5} more")
            
            if dry_run:
                print(f"\n[DRY-RUN] Would delete {len(events_to_remove)} events")
                return len(events_to_remove)
            
            # Confirm deletion
            confirm = input(f"\nDelete these {len(events_to_remove)} events? (yes/no): ")
            if confirm.lower() != 'yes':
                print("[CANCELLED] Deletion aborted")
                return 0
            
            # Delete events
            deleted_count = 0
            for event in events_to_remove:
                try:
                    client.table('events').delete().eq('event_hash', event['event_hash']).execute()
                    deleted_count += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to delete {event.get('title')}: {e}")
            
            print(f"[OK] Deleted {deleted_count} events")
            return deleted_count
            
        except Exception as e:
            print(f"[ERROR] Failed to remove recent events: {e}")
            return 0
    
    async def remove_events_not_in_local(self, dry_run: bool = False) -> int:
        """Remove database events that no longer exist in local file"""
        client = self._get_db_connection()
        if not client:
            return 0
        
        try:
            # Get local hashes
            local_hashes = set()
            for event in self.local_events:
                event_hash = event.get('event_hash') or self._generate_event_hash(event)
                local_hashes.add(event_hash)
            
            print(f"\n[REMOVE ORPHANED DATABASE EVENTS]")
            print(f"Local events: {len(local_hashes)}")
            
            # Get all database events
            result = client.table('events').select('event_hash, title').execute()
            
            if not result.data:
                print("[OK] No events in database")
                return 0
            
            db_events = result.data
            orphaned = [e for e in db_events if e['event_hash'] not in local_hashes]
            
            if not orphaned:
                print("[OK] No orphaned events found")
                return 0
            
            print(f"Orphaned events to remove: {len(orphaned)}")
            for event in orphaned[:5]:
                print(f"  - {event.get('title', 'Untitled')}")
            
            if len(orphaned) > 5:
                print(f"  ... and {len(orphaned) - 5} more")
            
            if dry_run:
                print(f"\n[DRY-RUN] Would delete {len(orphaned)} orphaned events")
                return len(orphaned)
            
            # Delete orphaned events
            confirm = input(f"\nDelete these {len(orphaned)} orphaned events? (yes/no): ")
            if confirm.lower() != 'yes':
                print("[CANCELLED] Deletion aborted")
                return 0
            
            deleted_count = 0
            for event in orphaned:
                try:
                    client.table('events').delete().eq('event_hash', event['event_hash']).execute()
                    deleted_count += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to delete {event.get('title')}: {e}")
            
            print(f"[OK] Deleted {deleted_count} orphaned events")
            return deleted_count
            
        except Exception as e:
            print(f"[ERROR] Failed to remove orphaned events: {e}")
            return 0
    
    async def compare_local_vs_db(self) -> Dict:
        """Compare local events with database events"""
        client = self._get_db_connection()
        if not client:
            return {}
        
        try:
            # Get local hashes
            local_hashes = {}
            for event in self.local_events:
                event_hash = event.get('event_hash') or self._generate_event_hash(event)
                local_hashes[event_hash] = event
            
            # Get DB events
            result = client.table('events').select('event_hash, title, created_at').execute()
            db_events = {e['event_hash']: e for e in result.data} if result.data else {}
            
            print(f"\n[COMPARE LOCAL VS DATABASE]")
            print(f"Local events: {len(local_hashes)}")
            print(f"Database events: {len(db_events)}")
            
            # Find differences
            only_local = set(local_hashes.keys()) - set(db_events.keys())
            only_db = set(db_events.keys()) - set(local_hashes.keys())
            in_both = set(local_hashes.keys()) & set(db_events.keys())
            
            print(f"\nOnly in local (not synced): {len(only_local)}")
            print(f"Only in database (orphaned): {len(only_db)}")
            print(f"In both: {len(in_both)}")
            
            if only_local:
                print("\nFirst 5 local-only events:")
                for hash_val in list(only_local)[:5]:
                    event = local_hashes[hash_val]
                    print(f"  - {event.get('title', 'Untitled')}")
            
            if only_db:
                print("\nFirst 5 database-only events:")
                for hash_val in list(only_db)[:5]:
                    event = db_events[hash_val]
                    print(f"  - {event.get('title', 'Untitled')}")
            
            return {
                'local_count': len(local_hashes),
                'db_count': len(db_events),
                'only_local': len(only_local),
                'only_db': len(only_db),
                'in_both': len(in_both),
                'only_local_hashes': list(only_local),
                'only_db_hashes': list(only_db)
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to compare: {e}")
            return {}
    
    async def batch_update_by_criteria(self, field: str, old_value: str, new_value: str, 
                                      dry_run: bool = False) -> int:
        """Batch update events matching criteria"""
        client = self._get_db_connection()
        if not client:
            return 0
        
        try:
            # Find matching events
            result = client.table('events').select('event_hash, title').eq(field, old_value).execute()
            
            if not result.data:
                print(f"[OK] No events found with {field}='{old_value}'")
                return 0
            
            matching = result.data
            print(f"\n[BATCH UPDATE]")
            print(f"Found {len(matching)} events with {field}='{old_value}':")
            
            for event in matching[:5]:
                print(f"  - {event.get('title', 'Untitled')}")
            
            if dry_run:
                print(f"\n[DRY-RUN] Would update {len(matching)} events")
                return len(matching)
            
            # Confirm
            confirm = input(f"\nUpdate {field} from '{old_value}' to '{new_value}' for {len(matching)} events? (yes/no): ")
            if confirm.lower() != 'yes':
                print("[CANCELLED]")
                return 0
            
            # Update
            client.table('events').update({field: new_value}).eq(field, old_value).execute()
            print(f"[OK] Updated {len(matching)} events")
            return len(matching)
            
        except Exception as e:
            print(f"[ERROR] Batch update failed: {e}")
            return 0


def main():
    parser = argparse.ArgumentParser(
        description='Database Maintenance & Repair Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Update specific event by hash
    python db_maintenance.py --update-by-hash abc123 --field description --value "New description"
    
    # Update event by link
    python db_maintenance.py --update-by-link "https://eventbrite.com/e/123" --field title --value "New Title"
    
    # Sync all patched local events to database
    python db_maintenance.py --sync-patched
    
    # Remove events added in last 24 hours
    python db_maintenance.py --remove-recent --hours 24
    
    # Remove DB events not in local file
    python db_maintenance.py --remove-orphaned
    
    # Compare local vs database
    python db_maintenance.py --compare
    
    # Batch update (e.g., fix category)
    python db_maintenance.py --batch-update --field category --from "Concert" --to "Music"
    
    # Dry run (preview changes)
    python db_maintenance.py --sync-patched --dry-run
        """
    )
    
    parser.add_argument('--events-file', default='all_events.json',
                       help='Path to local events file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without applying')
    
    # Single event updates
    parser.add_argument('--update-by-hash',
                       help='Update event with specific hash')
    parser.add_argument('--update-by-link',
                       help='Update event with specific link')
    parser.add_argument('--field',
                       help='Field to update')
    parser.add_argument('--value',
                       help='New value for field')
    
    # Bulk operations
    parser.add_argument('--sync-patched', action='store_true',
                       help='Update DB events from patched local data')
    parser.add_argument('--remove-recent', action='store_true',
                       help='Remove recently added events')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours back for recent events (default: 24)')
    parser.add_argument('--remove-orphaned', action='store_true',
                       help='Remove DB events not in local file')
    
    # Analysis
    parser.add_argument('--compare', action='store_true',
                       help='Compare local vs database events')
    
    # Batch updates
    parser.add_argument('--batch-update', action='store_true',
                       help='Batch update events by criteria')
    parser.add_argument('--from',
                       dest='from_value',
                       help='Current value to match')
    parser.add_argument('--to',
                       dest='to_value',
                       help='New value to set')
    
    args = parser.parse_args()
    
    # Initialize tool
    tool = DatabaseMaintenanceTool(events_file=args.events_file)
    
    # Execute command
    if args.update_by_hash:
        if not args.field or args.value is None:
            print("[ERROR] --field and --value required for update")
            return
        asyncio.run(tool.update_event_by_hash(
            args.update_by_hash,
            {args.field: args.value}
        ))
    
    elif args.update_by_link:
        if not args.field or args.value is None:
            print("[ERROR] --field and --value required for update")
            return
        asyncio.run(tool.update_event_by_link(
            args.update_by_link,
            {args.field: args.value}
        ))
    
    elif args.sync_patched:
        asyncio.run(tool.update_all_from_local(dry_run=args.dry_run))
    
    elif args.remove_recent:
        asyncio.run(tool.remove_recent_events(
            hours=args.hours,
            dry_run=args.dry_run
        ))
    
    elif args.remove_orphaned:
        asyncio.run(tool.remove_events_not_in_local(dry_run=args.dry_run))
    
    elif args.compare:
        asyncio.run(tool.compare_local_vs_db())
    
    elif args.batch_update:
        if not args.field or not args.from_value or args.to_value is None:
            print("[ERROR] --field, --from, and --to required for batch update")
            return
        asyncio.run(tool.batch_update_by_criteria(
            args.field,
            args.from_value,
            args.to_value,
            dry_run=args.dry_run
        ))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
