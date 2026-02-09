#!/usr/bin/env python3
"""
Database synchronization module for Supabase
Enhanced with email subscription support and frontend integration

Handles:
- Data validation and standardization
- Batch insertion to Supabase
- Deduplication tracking
- Email subscription syncing
- Price tier and category tagging
- Frontend live update triggering
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import hashlib
from config_loader import get_config

# Load environment variables from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load from .env file in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=False)
        print(f"[OK] Loaded environment from {env_path}")
    else:
        # Try parent directory (project root)
        parent_env = os.path.join(script_dir, '..', '.env')
        if os.path.exists(parent_env):
            load_dotenv(dotenv_path=parent_env, override=False)
            print(f"[OK] Loaded environment from {parent_env}")
        else:
            print("[WARN] No .env file found, using global environment variables")
except ImportError:
    print("[WARN] python-dotenv not installed, using global environment variables only")
    pass


class EventDataValidator:
    """Validate and standardize event data"""
    
    # Price tier mapping
    PRICE_TIERS = {
        0: "Free",
        1: "<$20",
        2: "<$50",
        3: "<$100",
        4: "$100+"
    }
    
    # Default categories
    DEFAULT_CATEGORIES = [
        "Concert", "Nightlife", "Club", "Workshop", "Networking",
        "Sports", "Arts", "Food", "Community", "Tech", "Business", "Other"
    ]
    
    @staticmethod
    def categorize_event(event: Dict) -> str:
        """
        Categorize event based on title and description
        Uses keywords to assign to one of the default categories
        """
        text = f"{event.get('title', '')} {event.get('description', '')}".lower()
        
        category_keywords = {
            "Concert": ["concert", "music", "band", "dj", "performance", "show", "festival"],
            "Nightlife": ["club", "bar", "lounge", "nightlife", "dancing", "party"],
            "Workshop": ["workshop", "class", "training", "tutorial", "seminar", "course"],
            "Networking": ["networking", "meetup", "conference", "summit", "forum"],
            "Sports": ["sports", "game", "tournament", "match", "fitness", "yoga", "run"],
            "Arts": ["art", "gallery", "exhibition", "theater", "film", "screening", "show"],
            "Food": ["food", "restaurant", "tasting", "cooking", "brunch", "dinner"],
            "Community": ["community", "social", "gathering", "event", "celebration"],
            "Tech": ["tech", "startup", "coding", "development", "innovation", "app"],
            "Business": ["business", "entrepreneurship", "investment", "startup", "finance"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return "Other"
    
    @staticmethod
    def determine_price_tier(event: Dict) -> int:
        """
        Determine price tier from event price
        Returns: 0=Free, 1=<$20, 2=<$50, 3=<$100, 4=$100+
        """
        try:
            price = int(event.get('price', 0))
            if price == 0:
                return 0
            elif price < 20:
                return 1
            elif price < 50:
                return 2
            elif price < 100:
                return 3
            else:
                return 4
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def clean_location(location: str) -> str:
        """Clean location string (remove zero-width characters, extra spaces)"""
        # Remove zero-width characters
        location = location.replace('\u200b', '').strip()
        # Clean up multiple spaces
        location = ' '.join(location.split())
        return location
    
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
        
        # City field (important for filtering)
        if 'city' in event and event['city']:
            cleaned['city'] = str(event['city']).strip()
        elif 'city_id' in event and event['city_id']:
            cleaned['city'] = str(event['city_id']).strip()
        
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
        
        # Validate date format (YYYY-MM-DD or flexible parsing)
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
        
        # Clean location (remove zero-width chars)
        if 'location' in cleaned:
            cleaned['location'] = EventDataValidator.clean_location(cleaned['location'])
        
        # Add computed fields
        cleaned['scraped_at'] = datetime.now(timezone.utc).isoformat()
        
        # 2D Tagging: Price Tier and Category
        cleaned['price_tier'] = EventDataValidator.determine_price_tier(cleaned)
        cleaned['category'] = EventDataValidator.categorize_event(cleaned)
        
        # Event hash for deduplication
        cleaned['event_hash'] = EventDataValidator.generate_event_hash(cleaned)
        
        return (len(errors) == 0, cleaned, errors)
    
    @staticmethod
    def generate_event_hash(event: Dict) -> str:
        """Generate unique hash for event deduplication"""
        key_parts = [
            event.get('title', '').lower().strip(),
            event.get('date', ''),
            event.get('location', '').lower().strip(),
            event.get('city', '').lower().strip(),
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
        self.events_table = 'events'
        self.subscriptions_table = 'email_subscriptions'
    
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
            print(f"[WARN] Skipping {len(invalid_events)} invalid events")
            for invalid in invalid_events[:5]:  # Show first 5 errors
                print(f"  - {invalid['event'].get('title', 'Unknown')}: {invalid['errors']}")
        
        if not valid_events:
            return (False, 0, ["No valid events to insert"])
        
        # Debug: Check if description is present in first event
        if valid_events:
            first_event = valid_events[0]
            print(f"✓ First event has description: {'description' in first_event}")
            print(f"✓ Description length: {len(first_event.get('description', ''))} chars")
        
        try:
            # Import Supabase client (lazy load)
            from supabase import create_client, Client
            
            client: Client = create_client(self.api_url, self.api_key)
            
            # Check for existing events by hash and link
            existing_hashes = set()
            existing_links = set()
            try:
                response = client.table(self.events_table).select('event_hash,link').execute()
                if response.data:
                    existing_hashes = {row['event_hash'] for row in response.data}
                    existing_links = {row['link'] for row in response.data}
            except Exception as e:
                print(f"[WARN] Could not check existing events: {e}")
            
            # Filter out events already in DB by hash or link, and deduplicate by link within batch
            seen_links = set()
            new_events = []
            for e in valid_events:
                link = e.get('link', '')
                if e.get('event_hash') in existing_hashes:
                    continue
                if link in existing_links or link in seen_links:
                    continue
                seen_links.add(link)
                new_events.append(e)
            
            skipped = len(valid_events) - len(new_events)
            if skipped > 0:
                print(f"[INFO] Skipping {skipped} events already in database")
            
            if not new_events:
                return (True, 0, [])
            
            print(f"[INFO] Inserting {len(new_events)} new events...")
            
            batch_size = 100
            total_inserted = 0
            total_skipped = 0
            
            for i in range(0, len(new_events), batch_size):
                batch = new_events[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                try:
                    response = client.table(self.events_table).insert(batch).execute()
                    inserted = len(response.data) if response.data else len(batch)
                    total_inserted += inserted
                    print(f"  Batch {batch_num}: inserted {inserted} events")
                except Exception as e:
                    error_msg = str(e)
                    if 'duplicate' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                        print(f"  Batch {batch_num}: conflict, inserting one-by-one...")
                        for event in batch:
                            try:
                                resp = client.table(self.events_table).insert(event).execute()
                                total_inserted += 1
                            except Exception:
                                total_skipped += 1
                    else:
                        return (False, total_inserted, [f"Batch insert failed: {error_msg}"])
            
            if total_skipped > 0:
                print(f"[INFO] Skipped {total_skipped} conflicting events during insert")
            
            return (True, total_inserted, [])
            
        except ImportError:
            return (False, 0, ["Supabase client not installed: pip install supabase"])
        except Exception as e:
            return (False, 0, [f"Database error: {str(e)}"])
    
    async def insert_email_subscription(self, email: str, city: str) -> Tuple[bool, str]:
        """
        Insert or update email subscription
        
        Args:
            email: User email address
            city: City code (e.g., 'ca--los-angeles')
        
        Returns:
            (success, message)
        """
        if not self.is_configured():
            return (False, "Supabase not configured")
        
        try:
            from supabase import create_client
            
            client = create_client(self.api_url, self.api_key)
            
            # Validate email format
            if not self._validate_email(email):
                return (False, "Invalid email format")
            
            # Check if subscription exists
            try:
                response = client.table(self.subscriptions_table)\
                    .select('*')\
                    .eq('email', email)\
                    .eq('city', city)\
                    .execute()
                
                if response.data:
                    # Update existing subscription
                    client.table(self.subscriptions_table)\
                        .update({
                            'updated_at': datetime.utcnow().isoformat(),
                            'is_active': True
                        })\
                        .eq('email', email)\
                        .eq('city', city)\
                        .execute()
                    
                    return (True, f"Subscription updated for {email} in {city}")
                else:
                    # Create new subscription
                    client.table(self.subscriptions_table)\
                        .insert({
                            'email': email,
                            'city': city,
                            'is_active': True,
                            'created_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        })\
                        .execute()
                    
                    return (True, f"Subscription created for {email} in {city}")
            
            except Exception as e:
                return (False, f"Subscription error: {str(e)}")
        
        except ImportError:
            return (False, "Supabase client not installed")
        except Exception as e:
            return (False, f"Error: {str(e)}")
    
    async def unsubscribe_email(self, email: str, city: Optional[str] = None) -> Tuple[bool, str]:
        """
        Unsubscribe email from a city (or all cities if city is None)
        
        Args:
            email: User email address
            city: City code, or None to unsubscribe from all cities
        
        Returns:
            (success, message)
        """
        if not self.is_configured():
            return (False, "Supabase not configured")
        
        try:
            from supabase import create_client
            
            client = create_client(self.api_url, self.api_key)
            
            if city:
                # Unsubscribe from specific city
                client.table(self.subscriptions_table)\
                    .update({'is_active': False})\
                    .eq('email', email)\
                    .eq('city', city)\
                    .execute()
                return (True, f"Unsubscribed {email} from {city}")
            else:
                # Unsubscribe from all cities
                client.table(self.subscriptions_table)\
                    .update({'is_active': False})\
                    .eq('email', email)\
                    .execute()
                return (True, f"Unsubscribed {email} from all cities")
        
        except Exception as e:
            return (False, f"Unsubscribe error: {str(e)}")
    
    @staticmethod
    def _validate_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


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
                return {'events': {}, 'last_updated': None}
        return {'events': {}, 'last_updated': None}

    def _save_tracker(self) -> None:
        """Save tracker"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)

    def add_events(self, events: List[Dict], db_synced: bool = True) -> None:
        """Add events to tracker. Only marks as db_synced if actually synced to database."""
        for event in events:
            event_hash = event.get('event_hash', EventDataValidator.generate_event_hash(event))
            self.data['events'][event_hash] = {
                'title': event.get('title'),
                'date': event.get('date'),
                'added_at': datetime.now(timezone.utc).isoformat(),
                'db_synced': db_synced
            }
        
        self.data['last_updated'] = datetime.now(timezone.utc).isoformat()
        self._save_tracker()

    def is_tracked(self, event_hash: str) -> bool:
        """Check if event already tracked AND synced to database"""
        entry = self.data['events'].get(event_hash)
        if not entry:
            return False
        return entry.get('db_synced', False)

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
    
    async def sync_events(self, events_file: str = None) -> Dict:
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
        
        # Resolve events file path - check current dir, then fronto/public
        if events_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(script_dir, "all_events.json"),
                os.path.join(script_dir, "..", "fronto", "src", "public", "all_events.json"),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    events_file = candidate
                    break
            if events_file is None:
                events_file = candidates[0]
        
        # Check if file exists
        if not os.path.exists(events_file):
            result['errors'].append(f"Events file not found: {events_file}")
            return result
        
        # Load events
        try:
            with open(events_file, 'r') as f:
                data = json.load(f)
                events = data.get('events', [])
                if not events and isinstance(data, dict) and data.get('cities'):
                    for _, city_block in data.get('cities', {}).items():
                        events.extend(city_block.get('events', []))
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON: {e}")
            return result
        except Exception as e:
            result['errors'].append(f"Error reading file: {e}")
            return result
        
        if not events:
            result['success'] = True
            return result
        
        print(f"Found {len(events)} events to sync...")
        
        # Sync to database if configured
        if self.sync.is_configured():
            success, inserted, errors = await self.sync.insert_events(events)
            result['success'] = success
            result['events_synced'] = inserted
            result['errors'].extend(errors)
            
            # Track all events that are confirmed in the DB (inserted or already there as duplicates)
            if success:
                self.tracker.add_events(events, db_synced=True)
        else:
            print("⚠ Supabase not configured, skipping database sync")
            result['errors'].append("Supabase not configured: check SUPABASE_URL and SUPABASE_KEY")
            result['success'] = False
            
            # Clean up old events from tracker
            removed = self.tracker.remove_past_events(days=30)
            result['past_events_removed'] = removed
            # NOTE: keep events file for frontend cache
        
        return result


async def main():
    """Test database sync"""
    manager = DatabaseSyncManager()
    
    # Debug: Show Supabase configuration status
    print("\n=== SUPABASE CONFIG ===")
    print(f"Supabase configured: {manager.sync.is_configured()}")
    if manager.sync.api_url:
        print(f"Supabase URL: {manager.sync.api_url[:30]}...")
    else:
        print("Supabase URL: NOT SET")
    if manager.sync.api_key:
        print(f"Supabase Key: {'*' * 10}...{manager.sync.api_key[-4:]}")
    else:
        print("Supabase Key: NOT SET")
    
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




