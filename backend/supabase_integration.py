#!/usr/bin/env python3
"""
Supabase integration for Nocturne event platform.
Syncs event data to Supabase PostgreSQL for real-time updates and multi-user sharing.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

try:
    from supabase import create_client, Client
except ImportError:
    print("Warning: supabase not installed. Install with: pip install supabase")
    create_client = None
    Client = None

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Manages Supabase connection and operations"""
    
    def __init__(self):
        self.url = os.environ.get('SUPABASE_URL')
        self.key = os.environ.get('SUPABASE_KEY')
        self.client: Optional[Client] = None
        self.connected = False
        
        if self.url and self.key and create_client:
            try:
                self.client = create_client(self.url, self.key)
                self.connected = True
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.connected = False
        else:
            if not self.url or not self.key:
                logger.warning("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
            if not create_client:
                logger.warning("supabase package not installed")
    
    async def sync_events(self, events_data: List[Dict], city: str) -> Dict:
        """
        Sync events to Supabase while preserving local database as primary storage.
        This allows real-time updates across all users viewing the same city.
        """
        if not self.connected or not self.client:
            logger.warning("Supabase not connected, skipping sync")
            return {"status": "skipped", "reason": "Supabase not configured"}
        
        try:
            synced_count = 0
            updated_count = 0
            
            for event in events_data:
                # Prepare event data for Supabase, ensuring city is properly set
                supabase_event = {
                    "title": event.get('title'),
                    "link": event.get('link'),
                    "date": event.get('date'),
                    "time": event.get('time'),
                    "location": event.get('location'),
                    "description": event.get('description'),
                    "source": event.get('source', 'unknown'),
                    "city": event.get('city', city),  # Use event's city if available, otherwise use passed city
                    "synced_at": datetime.utcnow().isoformat(),
                    "last_scraped": datetime.utcnow().isoformat()
                }
                
                try:
                    # Try to find existing event by link
                    existing = self.client.table('events').select('id').eq(
                        'link', event.get('link')
                    ).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        # Update existing event
                        self.client.table('events').update(
                            supabase_event
                        ).eq('link', event.get('link')).execute()
                        updated_count += 1
                    else:
                        # Insert new event
                        self.client.table('events').insert(supabase_event).execute()
                        synced_count += 1
                
                except Exception as e:
                    logger.error(f"Failed to sync event {event.get('title')}: {e}")
                    continue
            
            logger.info(f"Supabase sync complete: {synced_count} new, {updated_count} updated")
            return {
                "status": "success",
                "synced": synced_count,
                "updated": updated_count
            }
        
        except Exception as e:
            logger.error(f"Supabase sync failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_events_since(self, city: str, since: str) -> List[Dict]:
        """
        Fetch events from Supabase that were added/updated since a specific time.
        Used for live updates during scraping.
        """
        if not self.connected or not self.client:
            logger.warning("Supabase not connected")
            return []
        
        try:
            response = self.client.table('events').select('*').eq(
                'city', city
            ).gte('last_scraped', since).order(
                'synced_at', desc=True
            ).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Failed to fetch recent events from Supabase: {e}")
            return []
    
    async def get_city_events(self, city: str, limit: int = 100) -> List[Dict]:
        """
        Fetch all events for a city from Supabase.
        """
        if not self.connected or not self.client:
            logger.warning("Supabase not connected")
            return []
        
        try:
            response = self.client.table('events').select('*').eq(
                'city', city
            ).order('date').limit(limit).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Failed to fetch events from Supabase: {e}")
            return []
    
    async def create_tables(self) -> bool:
        """
        Create required Supabase tables if they don't exist.
        Note: Supabase tables should typically be created via the dashboard,
        but this helper documents the required schema.
        """
        if not self.connected or not self.client:
            logger.warning("Supabase not connected")
            return False
        
        logger.info("""
        Create the following tables in Supabase SQL Editor:
        
        -- Events table
        CREATE TABLE events (
            id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            date DATE NOT NULL,
            time TEXT,
            location TEXT,
            description TEXT,
            source TEXT,
            city TEXT NOT NULL,
            synced_at TIMESTAMP DEFAULT now(),
            last_scraped TIMESTAMP DEFAULT now(),
            created_at TIMESTAMP DEFAULT now()
        );
        
        CREATE INDEX idx_events_city ON events(city);
        CREATE INDEX idx_events_city_date ON events(city, date);
        CREATE INDEX idx_events_last_scraped ON events(last_scraped DESC);
        
        -- Subscriptions table
        CREATE TABLE subscriptions (
            id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
            email TEXT NOT NULL,
            city TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT now(),
            unsubscribed_at TIMESTAMP,
            UNIQUE(email, city)
        );
        
        CREATE INDEX idx_subscriptions_email ON subscriptions(email);
        CREATE INDEX idx_subscriptions_city ON subscriptions(city, is_active);
        """)
        
        return True


# Global Supabase manager instance
supabase_manager = SupabaseManager()


async def sync_events_to_supabase(events_data: List[Dict], city: str) -> Dict:
    """
    Wrapper function to sync events to Supabase.
    Should be called after local database save.
    """
    return await supabase_manager.sync_events(events_data, city)


async def get_recent_events_from_supabase(city: str, minutes: int = 5) -> List[Dict]:
    """
    Get events added in the last N minutes from Supabase.
    Useful for checking for new scraped events in real-time.
    """
    from datetime import timedelta
    since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
    return await supabase_manager.get_events_since(city, since)
