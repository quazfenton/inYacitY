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
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import hashlib
from config_loader import get_config
import re


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
    def parse_flexible_date(date_str: str) -> Optional[str]:
        """
        Parse various date formats and return standardized YYYY-MM-DD format
        
        Supported formats:
        - Mon, Feb 9
        - Sat, Feb 7
        - YYYY-MM-DD
        - MM/DD/YYYY
        - DD/MM/YYYY
        - Month DD, YYYY
        - DD Month YYYY
        """
        if not date_str:
            return None
            
        # Remove extra whitespace
        date_str = date_str.strip()
        
        # Define common date patterns and their corresponding format strings
        patterns = [
            # Mon, Feb 9 or Sat, Feb 7
            (r'^[A-Za-z]{3},\s*[A-Za-z]{3}\s*(\d{1,2})$', '%a, %b %d'),
            # Mon, Feb 9, YYYY
            (r'^[A-Za-z]{3},\s*[A-Za-z]{3}\s*(\d{1,2}),\s*(\d{4})$', '%a, %b %d, %Y'),
            # YYYY-MM-DD
            (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
            # MM/DD/YYYY or MM/DD/YY
            (r'^\d{1,2}/\d{1,2}/\d{4}$', '%m/%d/%Y'),
            (r'^\d{1,2}/\d{1,2}/\d{2}$', '%m/%d/%y'),
            # DD/MM/YYYY or DD/MM/YY
            (r'^\d{1,2}/\d{1,2}/\d{4}$', '%d/%m/%Y'),
            (r'^\d{1,2}/\d{1,2}/\d{2}$', '%d/%m/%y'),
            # Month DD, YYYY (e.g., Feb 9, 2026)
            (r'^[A-Za-z]{3}\s+\d{1,2},\s*\d{4}$', '%b %d, %Y'),
            # Full Month DD, YYYY (e.g., February 9, 2026)
            (r'^[A-Za-z]+\s+\d{1,2},\s*\d{4}$', '%B %d, %Y'),
            # DD Month YYYY
            (r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$', '%d %b %Y'),
            # DD Full Month YYYY
            (r'^\d{1,2}\s+[A-Za-z]+\s+\d{4}$', '%d %B %Y'),
            # Month DD (abbreviated, e.g., Feb 9)
            (r'^[A-Za-z]{3}\s+\d{1,2}$', '%b %d'),
            # Month DD (full, e.g., February 9)
            (r'^[A-Za-z]+\s+\d{1,2}$', '%B %d'),
        ]
        
        for pattern, fmt in patterns:
            if re.match(pattern, date_str):
                try:
                    # Check if the date string actually contains a 4-digit year
                    has_year = bool(re.search(r'\d{4}', date_str))
                    
                    if '%Y' not in fmt:
                        # Format doesn't include year, so we need to add it
                        current_year = datetime.now().year
                        formatted_date = f"{date_str}, {current_year}"
                        parsed_date = datetime.strptime(formatted_date, f'{fmt}, %Y')
                    elif not has_year:
                        # Format expects year but date string doesn't have it
                        current_year = datetime.now().year
                        formatted_date = f"{date_str}, {current_year}"
                        parsed_date = datetime.strptime(formatted_date, f'{fmt}, %Y')
                    else:
                        # Both format and date string have year
                        parsed_date = datetime.strptime(date_str, fmt)

                    # Handle cases where the parsed date is in the past but we expect future dates
                    # If the parsed date is in the past compared to current date, assume next year
                    today = datetime.now()
                    if parsed_date < today:
                        # Check if the date is just a few days in the past, possibly meaning next year
                        # For example, if today is Dec 30 and the event is Jan 2, it's probably next year
                        if parsed_date.month < today.month or (parsed_date.month == today.month and parsed_date.day < today.day):
                            # If the month is earlier in the year, assume it's for next year
                            parsed_date = parsed_date.replace(year=today.year + 1)

                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue  # Try next pattern
        
        # If no pattern matched, return None
        return None

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

        # Validate and normalize date format
        if 'date' in cleaned:
            normalized_date = EventDataValidator.parse_flexible_date(cleaned['date'])
            if normalized_date:
                cleaned['date'] = normalized_date  # Replace with normalized date
            else:
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
        try:
            cleaned['scraped_at'] = datetime.now(datetime.timezone.utc).isoformat()
        except AttributeError:
            # Fallback for older Python versions
            from datetime import timezone
            try:
                cleaned['scraped_at'] = datetime.now(timezone.utc).isoformat()
            except AttributeError:
                # Even older Python versions
                cleaned['scraped_at'] = datetime.utcnow().isoformat()

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
            print(f"⚠ Skipping {len(invalid_events)} invalid events")
            for invalid in invalid_events[:5]:  # Show first 5 errors
                print(f"  - {invalid['event'].get('title', 'Unknown')}: {invalid['errors']}")
        
        if not valid_events:
            return (False, 0, ["No valid events to insert"])
        
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
                print(f"⚠ Could not check for existing events: {e}")
            
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
                    # Prepare update data with timezone-safe datetime
                    try:
                        updated_at_value = datetime.now(datetime.timezone.utc).isoformat()
                    except AttributeError:
                        # Fallback for older Python versions
                        from datetime import timezone
                        try:
                            updated_at_value = datetime.now(timezone.utc).isoformat()
                        except AttributeError:
                            # Even older Python versions
                            updated_at_value = datetime.utcnow().isoformat()
                    
                    client.table(self.subscriptions_table)\
                        .update({
                            'updated_at': updated_at_value,
                            'is_active': True
                        })\
                        .eq('email', email)\
                        .eq('city', city)\
                        .execute()
                    
                    return (True, f"Subscription updated for {email} in {city}")
                else:
                    # Create new subscription
                    # Prepare timestamps with timezone-safe datetime
                    try:
                        timestamp = datetime.now(datetime.timezone.utc).isoformat()
                    except AttributeError:
                        # Fallback for older Python versions
                        from datetime import timezone
                        try:
                            timestamp = datetime.now(timezone.utc).isoformat()
                        except AttributeError:
                            # Even older Python versions
                            timestamp = datetime.utcnow().isoformat()
                    
                    client.table(self.subscriptions_table)\
                        .insert({
                            'email': email,
                            'city': city,
                            'is_active': True,
                            'created_at': timestamp,
                            'updated_at': timestamp
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
            except:
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
            
            # Prepare timestamp with timezone-safe datetime
            try:
                added_at_value = datetime.now(datetime.timezone.utc).isoformat()
            except AttributeError:
                # Fallback for older Python versions
                from datetime import timezone
                try:
                    added_at_value = datetime.now(timezone.utc).isoformat()
                except AttributeError:
                    # Even older Python versions
                    added_at_value = datetime.utcnow().isoformat()
            
            self.data['events'][event_hash] = {
                'title': event.get('title'),
                'date': event.get('date'),
                'added_at': added_at_value,
                'db_synced': db_synced
            }
        
        # Prepare timestamp with timezone-safe datetime
        try:
            last_updated_value = datetime.now(datetime.timezone.utc).isoformat()
        except AttributeError:
            # Fallback for older Python versions
            from datetime import timezone
            try:
                last_updated_value = datetime.now(timezone.utc).isoformat()
            except AttributeError:
                # Even older Python versions
                last_updated_value = datetime.utcnow().isoformat()
        
        self.data['last_updated'] = last_updated_value
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
                os.path.join(script_dir, "..", "fronto", "public", "all_events.json"),
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
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON: {e}")
            return result
        except Exception as e:
            result['errors'].append(f"Error reading file: {e}")
            return result

        if not events:
            if self.sync.is_configured():
                result['success'] = True
            else:
                result['errors'].append("Supabase not configured: cannot sync empty events")
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
        db_actually_synced = False
        if self.sync.is_configured():
            success, inserted, errors = await self.sync.insert_events(new_events)
            result['success'] = success
            result['events_synced'] = inserted
            result['errors'].extend(errors)
            db_actually_synced = success
        else:
            print("⚠ Supabase not configured, skipping database sync")
            result['success'] = True
            result['events_synced'] = len(new_events)
        
        # Add new events to tracker — only mark db_synced if actually inserted into DB
        if result['success']:
            self.tracker.add_events(new_events, db_synced=db_actually_synced)
            
            # Clean up old events from tracker
            removed = self.tracker.remove_past_events(days=30)
            result['past_events_removed'] = removed
            
            # Clear events file after sync
            with open(events_file, 'w') as f:
                json.dump({'events': [], 'count': 0}, f)
        
        return result


async def main():
    """Test database sync"""
    manager = DatabaseSyncManager()
    
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
