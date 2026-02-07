#!/usr/bin/env python3
"""
Database synchronization module for Supabase
Handles:
- Data validation and standardization
- Batch insertion to Supabase
- Deduplication tracking
- Email subscription syncing
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import hashlib
from config_loader import get_config


class EventDataValidator:
    """Validate and standardize event data"""
    
    @staticmethod
    def validate_event(event: Dict) -> Tuple[bool, Dict, List[str]]:
        """
        Validate event data
        
        Returns:
            (is_valid, cleaned_event, errors)
        """
        errors = []
        cleaned = {}
        
        # Required fields
        required = ['title', 'date', 'location', 'link', 'source']
        for field in required:
            if field not in event or not event[field]:
                errors.append(f"Missing required field: {field}")
            else:
                cleaned[field] = str(event[field]).strip()
        
        # Optional fields with validation
        if 'time' in event:
            cleaned['time'] = str(event.get('time', 'TBA')).strip()
        else:
            cleaned['time'] = 'TBA'
        
        if 'description' in event:
            desc = str(event.get('description', '')).strip()
            # Limit description length
            cleaned['description'] = desc[:1000] if desc else ""
        else:
            cleaned['description'] = ""
        
        # Validate date format (YYYY-MM-DD)
        if 'date' in cleaned:
            try:
                datetime.strptime(cleaned['date'], '%Y-%m-%d')
            except ValueError:
                errors.append(f"Invalid date format: {cleaned['date']}")
        
        # Validate URL
        if 'link' in cleaned:
            if not cleaned['link'].startswith(('http://', 'https://')):
                errors.append(f"Invalid URL format: {cleaned['link']}")
        
        # Price field (optional, default 0)
        if 'price' in event:
            try:
                cleaned['price'] = int(event['price'])
            except (ValueError, TypeError):
                cleaned['price'] = 0
        else:
            cleaned['price'] = 0
        
        # Add metadata
        cleaned['scraped_at'] = datetime.utcnow().isoformat()
        cleaned['event_hash'] = EventDataValidator.generate_event_hash(cleaned)
        
        return (len(errors) == 0, cleaned, errors)
    
    @staticmethod
    def generate_event_hash(event: Dict) -> str:
        """Generate unique hash for event deduplication"""
        key_parts = [
            event.get('title', '').lower().strip(),
            event.get('date', ''),
            event.get('location', '').lower().strip(),
            event.get('source', '')
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    @staticmethod
    def validate_batch(events: List[Dict]) -> Tuple[List[Dict], List[Dict], List[str]]:
        """
        Validate batch of events
        
        Returns:
            (valid_events, invalid_events, all_errors)
        """
        valid = []
        invalid = []
        all_errors = []
        
        for event in events:
            is_valid, cleaned, errors = EventDataValidator.validate_event(event)
            
            if is_valid:
                valid.append(cleaned)
            else:
                invalid.append({
                    'event': event,
                    'errors': errors
                })
                all_errors.extend(errors)
        
        return valid, invalid, all_errors


class SupabaseSync:
    """Supabase database synchronization"""
    
    def __init__(self, api_url: str = None, api_key: str = None):
        """Initialize Supabase connection"""
        self.api_url = api_url or os.environ.get('SUPABASE_URL')
        self.api_key = api_key or os.environ.get('SUPABASE_KEY')
        self.table_name = 'events'
    
    def is_configured(self) -> bool:
        """Check if Supabase is configured"""
        return bool(self.api_url and self.api_key)
    
    async def insert_events(self, events: List[Dict]) -> Tuple[bool, int, List[str]]:
        """
        Insert events into Supabase
        
        Returns:
            (success, inserted_count, errors)
        """
        if not self.is_configured():
            return (False, 0, ["Supabase not configured: missing URL or API key"])
        
        if not events:
            return (True, 0, [])
        
        # Validate all events first
        valid_events, invalid_events, errors = EventDataValidator.validate_batch(events)
        
        if invalid_events:
            print(f"⚠ Skipping {len(invalid_events)} invalid events")
            for invalid in invalid_events[:5]:  # Show first 5 errors
                print(f"  - {invalid['event'].get('title', 'Unknown')}: {invalid['errors']}")
        
        if not valid_events:
            return (False, 0, ["No valid events to insert"])
        
        try:
            # Import Supabase client (lazy load)
            from supabase import create_client, Client
            
            client: Client = create_client(self.api_url, self.api_key)
            
            # Check for duplicates by event_hash
            existing_hashes = set()
            try:
                response = client.table(self.table_name).select('event_hash').execute()
                existing_hashes = {row['event_hash'] for row in response.data if response.data}
            except Exception as e:
                print(f"⚠ Could not check for existing events: {e}")
            
            # Filter new events
            new_events = [e for e in valid_events if e['event_hash'] not in existing_hashes]
            
            if not new_events:
                return (True, 0, ["All events already exist in database"])
            
            # Insert in batches (Supabase batch limit)
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(new_events), batch_size):
                batch = new_events[i:i + batch_size]
                
                try:
                    response = client.table(self.table_name).insert(batch).execute()
                    total_inserted += len(batch)
                except Exception as e:
                    return (False, total_inserted, [f"Batch insert failed: {str(e)}"])
            
            return (True, total_inserted, [])
            
        except ImportError:
            return (False, 0, ["Supabase client not installed: pip install supabase"])
        except Exception as e:
            return (False, 0, [f"Database error: {str(e)}"])
    
    async def insert_email_subscription(self, email: str, city: str) -> Tuple[bool, str]:
        """Insert or update email subscription"""
        if not self.is_configured():
            return (False, "Supabase not configured")
        
        try:
            from supabase import create_client
            
            client = create_client(self.api_url, self.api_key)
            
            # Check if subscription exists
            try:
                response = client.table('email_subscriptions').select('*').eq('email', email).eq('city', city).execute()
                
                if response.data:
                    # Update existing
                    client.table('email_subscriptions').update({
                        'updated_at': datetime.utcnow().isoformat(),
                        'is_active': True
                    }).eq('email', email).eq('city', city).execute()
                    
                    return (True, f"Subscription updated for {email} in {city}")
                else:
                    # Create new
                    client.table('email_subscriptions').insert({
                        'email': email,
                        'city': city,
                        'is_active': True,
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }).execute()
                    
                    return (True, f"Subscription created for {email} in {city}")
            
            except Exception as e:
                return (False, f"Subscription error: {str(e)}")
                except ImportError:
                    return (False, "Supabase client not installed")
                except Exception as e:
                    return (False, f"Error: {str(e)}")


        class DeduplicationTracker:
            """Track events for deduplication across runs"""
    
            def __init__(self, tracker_file: str = "event_tracker.json"):
                self.tracker_file = tracker_file
                self.data = self._load_tracker()
    
            def _load_tracker(self) -> Dict:
                """Load existing tracker"""
                if os.path.exists(self.tracker_file):
                    try:
                        with open(self.tracker_file, 'r') as f:
                            return json.load(f)
                    except (json.JSONDecodeError, OSError):
                        # If file is corrupt or unreadable, start with empty tracker
                        return {'events': {}, 'last_updated': None}
                return {'events': {}, 'last_updated': None}
    
            def _save_tracker(self) -> None:
                """Save tracker"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def add_events(self, events: List[Dict]) -> None:
        """Add events to tracker"""
        for event in events:
            event_hash = event.get('event_hash', EventDataValidator.generate_event_hash(event))
            self.data['events'][event_hash] = {
                'title': event.get('title'),
                'date': event.get('date'),
                'added_at': datetime.utcnow().isoformat()
            }
        
        self.data['last_updated'] = datetime.utcnow().isoformat()
        self._save_tracker()
    
    def is_tracked(self, event_hash: str) -> bool:
        """Check if event already tracked"""
        return event_hash in self.data['events']
    
    def remove_past_events(self, days: int = 30) -> int:
        """Remove events with dates older than X days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        removed = 0
        
        hashes_to_remove = []
        for event_hash, event_data in self.data['events'].items():
            if event_data.get('date', '2099-12-31') < cutoff_date:
                hashes_to_remove.append(event_hash)
        
        for event_hash in hashes_to_remove:
            del self.data['events'][event_hash]
            removed += 1
        
        if removed > 0:
            self._save_tracker()
        
        return removed
    
    def get_stats(self) -> Dict:
        """Get tracker statistics"""
        return {
            'total_tracked': len(self.data['events']),
            'last_updated': self.data['last_updated']
        }


class DatabaseSyncManager:
    """Orchestrate database syncing"""
    
    def __init__(self):
        self.config = get_config()
        self.sync = SupabaseSync()
        self.tracker = DeduplicationTracker()
    
    async def should_sync(self, run_count: int = 1) -> bool:
        """Check if sync should happen based on config"""
        sync_mode = self.config.get('DATABASE.SYNC_MODE', 0)
        
        # 0 = disabled
        if sync_mode == 0:
            return False
        
        # 1-4 = batch mode (sync on every Nth run)
        if isinstance(sync_mode, int) and 1 <= sync_mode <= 4:
            return run_count % sync_mode == 0
        
        # 5+ = sync on every run
        return sync_mode >= 5
    
    async def sync_events(self, events_file: str = "all_events.json") -> Dict:
        """
        Sync events from file to database
        
        Returns:
            {
                'success': bool,
                'events_synced': int,
                'errors': [],
                'new_duplicates_removed': int,
                'past_events_removed': int
            }
        """
        result = {
            'success': False,
            'events_synced': 0,
            'errors': [],
            'new_duplicates_removed': 0,
            'past_events_removed': 0
        }
        
        # Check if file exists
        if not os.path.exists(events_file):
            result['errors'].append(f"Events file not found: {events_file}")
            return result
        
        # Load events
        try:
            with open(events_file, 'r') as f:
                data = json.load(f)
                events = data.get('events', [])
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON: {e}")
            return result
        except Exception as e:
            result['errors'].append(f"Error reading file: {e}")
            return result
        
        if not events:
            result['success'] = True
            return result
        
        # Filter out tracked events (duplicates)
        new_events = []
        for event in events:
            event_hash = event.get('event_hash', EventDataValidator.generate_event_hash(event))
            if not self.tracker.is_tracked(event_hash):
                new_events.append(event)
            else:
                result['new_duplicates_removed'] += 1
        
        if not new_events:
            result['success'] = True
            print("ℹ No new events to sync")
            return result
        
        print(f"Syncing {len(new_events)} events to database...")
        
        # Sync to database if configured
        if self.sync.is_configured():
            success, inserted, errors = await self.sync.insert_events(new_events)
            result['success'] = success
            result['events_synced'] = inserted
            result['errors'].extend(errors)
        else:
            print("⚠ Supabase not configured, skipping database sync")
            result['success'] = True
            result['events_synced'] = len(new_events)
        
        # Add new events to tracker
        if result['success']:
            self.tracker.add_events(new_events)
            
            # Clean up old events from tracker
            removed = self.tracker.remove_past_events(days=30)
            result['past_events_removed'] = removed
            
            # Clear events file after sync
            with open(events_file, 'w') as f:
                json.dump({'events': [], 'count': 0}, f)
        
        return result
    
    def get_dedup_stats(self) -> Dict:
        """Get deduplication tracking stats"""
        return self.tracker.get_stats()


async def main():
    """Test database sync"""
    manager = DatabaseSyncManager()
    
    # Check if should sync (for testing, assume run_count = 1)
    should_sync = await manager.should_sync(run_count=1)
    print(f"Should sync: {should_sync}")
    
    # Sync events
    result = await manager.sync_events()
    
    print("\n=== SYNC RESULT ===")
    print(f"Success: {result['success']}")
    print(f"Events synced: {result['events_synced']}")
    print(f"Duplicates removed: {result['new_duplicates_removed']}")
    print(f"Past events removed: {result['past_events_removed']}")
    
    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())
