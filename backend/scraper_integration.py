#!/usr/bin/env python3
"""
Integration module connecting scraper functionality to the database
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List

# Add scraper directory to path for direct imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
scraper_dir = os.path.join(backend_dir, 'scraper')

if scraper_dir not in sys.path:
    sys.path.insert(0, scraper_dir)

# Try to import, with better error handling
try:
    from database import save_events, get_active_subscribers
except ImportError:
    # If running directly from backend directory
    sys.path.insert(0, backend_dir)
    from database import save_events, get_active_subscribers

try:
    from config import CONFIG, load_config
except ImportError:
    # Create a default config if not available
    CONFIG = {
        'SUPPORTED_LOCATIONS': [
            'ca--los-angeles',
            'ny--new-york',
            'dc--washington',
            'fl--miami',
            'tx--houston',
            'il--chicago'
        ]
    }
    
    def load_config():
        return CONFIG

# City mapping from config to display names
CITY_MAPPING = {
    'ca--los-angeles': {
        'id': 'ca--los-angeles',
        'name': 'LOS ANGELES',
        'slug': 'los-angeles',
        'coordinates': {'lat': 34.0522, 'lng': -118.2437}
    },
    'ny--new-york': {
        'id': 'ny--new-york',
        'name': 'NEW YORK',
        'slug': 'new-york',
        'coordinates': {'lat': 40.7128, 'lng': -74.0060}
    },
    'dc--washington': {
        'id': 'dc--washington',
        'name': 'WASHINGTON DC',
        'slug': 'washington-dc',
        'coordinates': {'lat': 38.9072, 'lng': -77.0369}
    },
    'fl--miami': {
        'id': 'fl--miami',
        'name': 'MIAMI',
        'slug': 'miami',
        'coordinates': {'lat': 25.7617, 'lng': -80.1918}
    },
    'tx--houston': {
        'id': 'tx--houston',
        'name': 'HOUSTON',
        'slug': 'houston',
        'coordinates': {'lat': 29.7604, 'lng': -95.3698}
    },
    'il--chicago': {
        'id': 'il--chicago',
        'name': 'CHICAGO',
        'slug': 'chicago',
        'coordinates': {'lat': 41.8781, 'lng': -87.6298}
    },
    'az--phoenix': {
        'id': 'az--phoenix',
        'name': 'PHOENIX',
        'slug': 'phoenix',
        'coordinates': {'lat': 33.4484, 'lng': -112.0740}
    },
    'pa--philadelphia': {
        'id': 'pa--philadelphia',
        'name': 'PHILADELPHIA',
        'slug': 'philadelphia',
        'coordinates': {'lat': 39.9526, 'lng': -75.1652}
    },
    'tx--san-antonio': {
        'id': 'tx--san-antonio',
        'name': 'SAN ANTONIO',
        'slug': 'san-antonio',
        'coordinates': {'lat': 29.4241, 'lng': -98.4936}
    },
    'ca--san-diego': {
        'id': 'ca--san-diego',
        'name': 'SAN DIEGO',
        'slug': 'san-diego',
        'coordinates': {'lat': 32.7157, 'lng': -117.1611}
    },
    'tx--dallas': {
        'id': 'tx--dallas',
        'name': 'DALLAS',
        'slug': 'dallas',
        'coordinates': {'lat': 32.7767, 'lng': -96.7970}
    },
    'tx--austin': {
        'id': 'tx--austin',
        'name': 'AUSTIN',
        'slug': 'austin',
        'coordinates': {'lat': 30.2672, 'lng': -97.7431}
    },
    'wa--seattle': {
        'id': 'wa--seattle',
        'name': 'SEATTLE',
        'slug': 'seattle',
        'coordinates': {'lat': 47.6062, 'lng': -122.3321}
    },
    'co--denver': {
        'id': 'co--denver',
        'name': 'DENVER',
        'slug': 'denver',
        'coordinates': {'lat': 39.7392, 'lng': -104.9903}
    },
    'ma--boston': {
        'id': 'ma--boston',
        'name': 'BOSTON',
        'slug': 'boston',
        'coordinates': {'lat': 42.3601, 'lng': -71.0589}
    },
    'ga--atlanta': {
        'id': 'ga--atlanta',
        'name': 'ATLANTA',
        'slug': 'atlanta',
        'coordinates': {'lat': 33.7490, 'lng': -84.3880}
    },
    'nv--las-vegas': {
        'id': 'nv--las-vegas',
        'name': 'LAS VEGAS',
        'slug': 'las-vegas',
        'coordinates': {'lat': 36.1699, 'lng': -115.1398}
    },
    'mi--detroit': {
        'id': 'mi--detroit',
        'name': 'DETROIT',
        'slug': 'detroit',
        'coordinates': {'lat': 42.3314, 'lng': -83.0458}
    },
    'or--portland': {
        'id': 'or--portland',
        'name': 'PORTLAND',
        'slug': 'portland',
        'coordinates': {'lat': 45.5152, 'lng': -122.6784}
    },
    'nc--charlotte': {
        'id': 'nc--charlotte',
        'name': 'CHARLOTTE',
        'slug': 'charlotte',
        'coordinates': {'lat': 35.2271, 'lng': -80.8431}
    },
    'tn--nashville': {
        'id': 'tn--nashville',
        'name': 'NASHVILLE',
        'slug': 'nashville',
        'coordinates': {'lat': 36.1627, 'lng': -86.7816}
    },
    'ok--oklahoma-city': {
        'id': 'ok--oklahoma-city',
        'name': 'OKLAHOMA CITY',
        'slug': 'oklahoma-city',
        'coordinates': {'lat': 35.4676, 'lng': -97.5164}
    },
    'la--new-orleans': {
        'id': 'la--new-orleans',
        'name': 'NEW ORLEANS',
        'slug': 'new-orleans',
        'coordinates': {'lat': 29.9511, 'lng': -90.0715}
    },
    'fl--orlando': {
        'id': 'fl--orlando',
        'name': 'ORLANDO',
        'slug': 'orlando',
        'coordinates': {'lat': 28.5383, 'lng': -81.3792}
    },
    'fl--tampa': {
        'id': 'fl--tampa',
        'name': 'TAMPA',
        'slug': 'tampa',
        'coordinates': {'lat': 27.9506, 'lng': -82.4572}
    },
    'ca--san-jose': {
        'id': 'ca--san-jose',
        'name': 'SAN JOSE',
        'slug': 'san-jose',
        'coordinates': {'lat': 37.3382, 'lng': -121.8863}
    },
    'ca--san-francisco': {
        'id': 'ca--san-francisco',
        'name': 'SAN FRANCISCO',
        'slug': 'san-francisco',
        'coordinates': {'lat': 37.7749, 'lng': -122.4194}
    },
    'ny--buffalo': {
        'id': 'ny--buffalo',
        'name': 'BUFFALO',
        'slug': 'buffalo',
        'coordinates': {'lat': 42.8864, 'lng': -78.8784}
    },
    'oh--columbus': {
        'id': 'oh--columbus',
        'name': 'COLUMBUS',
        'slug': 'columbus',
        'coordinates': {'lat': 39.9612, 'lng': -82.9988}
    },
    'oh--cleveland': {
        'id': 'oh--cleveland',
        'name': 'CLEVELAND',
        'slug': 'cleveland',
        'coordinates': {'lat': 41.4993, 'lng': -81.6944}
    },
    'in--indianapolis': {
        'id': 'in--indianapolis',
        'name': 'INDIANAPOLIS',
        'slug': 'indianapolis',
        'coordinates': {'lat': 39.7684, 'lng': -86.1581}
    },
    'mo--kansas-city': {
        'id': 'mo--kansas-city',
        'name': 'KANSAS CITY',
        'slug': 'kansas-city',
        'coordinates': {'lat': 39.0997, 'lng': -94.5786}
    },
    'mo--st-louis': {
        'id': 'mo--st-louis',
        'name': 'ST. LOUIS',
        'slug': 'st-louis',
        'coordinates': {'lat': 38.6270, 'lng': -90.1994}
    },
    'ca--sacramento': {
        'id': 'ca--sacramento',
        'name': 'SACRAMENTO',
        'slug': 'sacramento',
        'coordinates': {'lat': 38.5816, 'lng': -121.4944}
    },
    'tx--fort-worth': {
        'id': 'tx--fort-worth',
        'name': 'FORT WORTH',
        'slug': 'fort-worth',
        'coordinates': {'lat': 32.7555, 'lng': -97.3308}
    },
    'va--richmond': {
        'id': 'va--richmond',
        'name': 'RICHMOND',
        'slug': 'richmond',
        'coordinates': {'lat': 37.5407, 'lng': -77.4360}
    },
    'mn--minneapolis': {
        'id': 'mn--minneapolis',
        'name': 'MINNEAPOLIS',
        'slug': 'minneapolis',
        'coordinates': {'lat': 44.9778, 'lng': -93.2650}
    },
    'wi--milwaukee': {
        'id': 'wi--milwaukee',
        'name': 'MILWAUKEE',
        'slug': 'milwaukee',
        'coordinates': {'lat': 43.0389, 'lng': -87.9065}
    },
    'ky--louisville': {
        'id': 'ky--louisville',
        'name': 'LOUISVILLE',
        'slug': 'louisville',
        'coordinates': {'lat': 38.2527, 'lng': -85.7585}
    },
    'sc--charleston': {
        'id': 'sc--charleston',
        'name': 'CHARLESTON',
        'slug': 'charleston-sc',
        'coordinates': {'lat': 32.7765, 'lng': -79.9311}
    },
    'al--birmingham': {
        'id': 'al--birmingham',
        'name': 'BIRMINGHAM',
        'slug': 'birmingham',
        'coordinates': {'lat': 33.5207, 'lng': -86.8025}
    },
    'ut--salt-lake-city': {
        'id': 'ut--salt-lake-city',
        'name': 'SALT LAKE CITY',
        'slug': 'salt-lake-city',
        'coordinates': {'lat': 40.7608, 'lng': -111.8910}
    },
    'nm--albuquerque': {
        'id': 'nm--albuquerque',
        'name': 'ALBUQUERQUE',
        'slug': 'albuquerque',
        'coordinates': {'lat': 35.0844, 'lng': -106.6504}
    }
}


import logging
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Lock to prevent concurrent scraper runs that could interfere with each other
scraper_lock = asyncio.Lock()

# Per-city scrape tracking file
SCRAPE_TRACKER_PATH = Path("logs") / "scrape_tracker.json"

# Cooldown constants (in minutes)
ON_DEMAND_COOLDOWN_MINUTES = 30
CRON_COOLDOWN_MINUTES = 360  # 6 hours

STALE_THRESHOLD_DAYS = 5
MAX_STALE_CITIES_PER_RUN = 3

def _load_scrape_tracker() -> Dict:
    """Load the scrape tracker from disk."""
    if SCRAPE_TRACKER_PATH.exists():
        try:
            with open(SCRAPE_TRACKER_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"cities": {}, "last_cron_index": -1}

def _save_scrape_tracker(tracker: Dict):
    """Save the scrape tracker to disk."""
    SCRAPE_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCRAPE_TRACKER_PATH, 'w') as f:
        json.dump(tracker, f, indent=2)

def record_scrape(city: str, source: str = "manual", events_found: int = 0):
    """Record that a city was scraped. Always updates the scrape date."""
    tracker = _load_scrape_tracker()
    now = datetime.utcnow().isoformat()
    prev = tracker["cities"].get(city, {})
    tracker["cities"][city] = {
        "last_scraped": now,
        "source": source,
        "events_found": events_found,
        "total_scrapes": prev.get("total_scrapes", 0) + 1
    }
    _save_scrape_tracker(tracker)

def get_city_scrape_info(city: str) -> Dict:
    """Get scrape info for a specific city."""
    tracker = _load_scrape_tracker()
    city_info = tracker["cities"].get(city, {})
    if not city_info:
        return {"last_scraped": None, "can_refresh": True, "cooldown_remaining_minutes": 0, "days_since_scrape": None}
    last_scraped = datetime.fromisoformat(city_info["last_scraped"])
    source = city_info.get("source", "unknown")
    cooldown = ON_DEMAND_COOLDOWN_MINUTES if source == "manual" else CRON_COOLDOWN_MINUTES
    elapsed = (datetime.utcnow() - last_scraped).total_seconds() / 60
    remaining = max(0, cooldown - elapsed)
    days_since = (datetime.utcnow() - last_scraped).total_seconds() / 86400
    return {
        "last_scraped": city_info["last_scraped"],
        "source": source,
        "events_found": city_info.get("events_found", 0),
        "total_scrapes": city_info.get("total_scrapes", 0),
        "can_refresh": remaining == 0,
        "cooldown_remaining_minutes": round(remaining, 1),
        "days_since_scrape": round(days_since, 1)
    }

def get_stale_cities(max_count: int = MAX_STALE_CITIES_PER_RUN, threshold_days: int = STALE_THRESHOLD_DAYS) -> List[str]:
    """Find cities whose last scrape is older than threshold_days. Returns up to max_count, oldest first."""
    supported_cities = CONFIG.get('SUPPORTED_LOCATIONS', [])
    stale = []
    now = datetime.utcnow()
    for city in supported_cities:
        info = get_city_scrape_info(city)
        if info["last_scraped"] is None:
            stale.append((city, 9999))
        else:
            days = info["days_since_scrape"]
            if days > threshold_days:
                stale.append((city, days))
    stale.sort(key=lambda x: x[1], reverse=True)
    return [city for city, _ in stale[:max_count]]

def get_all_scrape_info() -> Dict:
    """Get scrape info for all supported cities."""
    supported_cities = CONFIG.get('SUPPORTED_LOCATIONS', [])
    result = {}
    for city in supported_cities:
        result[city] = get_city_scrape_info(city)
    return result

def get_next_city_to_scrape() -> str:
    """Get the next city in rotation for the cron job."""
    supported_cities = CONFIG.get('SUPPORTED_LOCATIONS', [])
    if not supported_cities:
        return None
    tracker = _load_scrape_tracker()
    last_index = tracker.get("last_cron_index", -1)
    next_index = (last_index + 1) % len(supported_cities)
    tracker["last_cron_index"] = next_index
    _save_scrape_tracker(tracker)
    return supported_cities[next_index]

def can_scrape_city(city: str, source: str = "manual") -> tuple[bool, float]:
    """Check if a city can be scraped based on cooldown. Returns (can_scrape, remaining_minutes)."""
    info = get_city_scrape_info(city)
    if info["can_refresh"]:
        return True, 0
    if source == "cron":
        return True, 0
    return False, info["cooldown_remaining_minutes"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def scrape_city_events(city: str, source: str = "manual") -> Dict:
    """
    Scrape events for a specific city and save to database.
    Returns statistics about the scraping operation.
    """
    from run import run_all_scrapers
    import shutil

    logger.info(f"Starting scrape for city: {city} (source: {source})")

    # Load current config
    config = load_config()

    # Update config for this city
    config['LOCATION'] = city

    # Run the scrapers - use lock to prevent concurrent access to shared resources
    logger.info(f"Running scrapers for {city}...")

    # Scraper directory is at project root (same level as backend dir)
    scraper_dir = os.path.join(os.path.dirname(__file__), 'scraper')
    original_dir = os.getcwd()

    async with scraper_lock:
        # Save temporary config (inside the lock to prevent race conditions)
        # Merge with full scraper config to preserve city maps, browser, proxy settings
        config_path = os.path.join(scraper_dir, 'config.json')
        full_config_path = os.path.join(scraper_dir, 'config_sync.json')
        try:
            with open(full_config_path, 'r') as f:
                full = json.load(f)
                for k in ('BROWSER', 'SCRAPER_SETTINGS', 'PROXY_FALLBACK', 'DATA', 'OUTPUT', 'LOGGING'):
                    if k in full:
                        config.setdefault(k, full[k])
        except (json.JSONDecodeError, IOError):
            pass
        # Ensure LOCATION and SUPPORTED_LOCATIONS come from the backend
        config['LOCATION'] = city
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        try:
            os.chdir(scraper_dir)
            await run_all_scrapers()
        finally:
            os.chdir(original_dir)

        # Read the results while still holding the lock to prevent race condition
        all_events_file = os.path.join(scraper_dir, 'all_events.json')

        if not os.path.exists(all_events_file):
            logger.warning(f"No events found for {city}")
            record_scrape(city, source, 0)
            return {
                "city": city,
                "status": "error",
                "message": "No events found",
                "events_count": 0
            }

        # Read file contents while still in the lock to prevent race condition
        with open(all_events_file, 'r') as f:
            data = json.load(f)

    # Process data after releasing the lock
    # Try to get events from the root level first
    events_data = data.get('events', [])

    # If no events at root, try to get from cities structure
    if not events_data and 'cities' in data:
        city_data = data['cities'].get(city, {})
        events_data = city_data.get('events', [])

        # Do NOT aggregate events from all cities - only use events for the specific city
        # If no events found for the specific city, return an empty list

    # Add source to events if missing
    for event in events_data:
        if 'source' not in event:
            # Try to infer source from link
            link = event.get('link', '')
            if 'eventbrite.com' in link:
                event['source'] = 'eventbrite'
            elif 'meetup.com' in link:
                event['source'] = 'meetup'
            elif 'lu.ma' in link:
                event['source'] = 'luma'
            else:
                event['source'] = 'unknown'

    # Save to database
    logger.info(f"Saving {len(events_data)} events to database...")
    result = await save_events(events_data, city)

    logger.info(f"Saved {result['saved']} new events, updated {result['updated']} existing events")

    # Sync to Supabase if configured
    try:
        from supabase_integration import sync_events_to_supabase
        supabase_result = await sync_events_to_supabase(events_data, city)
        logger.info(f"Supabase sync result: {supabase_result}")
    except Exception as e:
        logger.warning(f"Supabase sync failed (non-critical): {e}")

    # Record the scrape
    record_scrape(city, source, len(events_data))

    return {
        "city": city,
        "status": "success",
        "events_scraped": len(events_data),
        "events_saved": result['saved'],
        "events_updated": result['updated']
    }


async def scrape_city_on_demand(city: str) -> Dict:
    """
    Scrape a city on-demand with cooldown enforcement.
    Returns error if cooldown is still active.
    """
    can_scrape, remaining = can_scrape_city(city, source="manual")
    if not can_scrape:
        return {
            "city": city,
            "status": "cooldown",
            "message": f"City was recently scraped. Try again in {remaining:.0f} minutes.",
            "cooldown_remaining_minutes": remaining
        }
    return await scrape_city_events(city, source="manual")


async def refresh_all_cities() -> Dict:
    """
    Scrape events for all supported cities.
    Returns aggregated statistics.
    """
    from run import run_all_scrapers

    supported_cities = CONFIG.get('SUPPORTED_LOCATIONS', [])

    results = {
        "total_cities": len(supported_cities),
        "successful": 0,
        "failed": 0,
        "total_events": 0,
        "city_results": []
    }

    logger.info(f"Starting refresh of {len(supported_cities)} cities...")

    for city in supported_cities:
        try:
            result = await scrape_city_events(city)

            if result['status'] == 'success':
                results['successful'] += 1
                results['total_events'] += result.get('events_scraped', 0)
            else:
                results['failed'] += 1

            results['city_results'].append(result)

            # Add a small delay between cities to avoid rate limiting
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error scraping {city}: {e}")
            results['failed'] += 1
            results['city_results'].append({
                "city": city,
                "status": "error",
                "error": str(e)
            })

    logger.info(f"Refresh complete. Success: {results['successful']}, Failed: {results['failed']}, Total events: {results['total_events']}")

    return results


async def send_weekly_digest(batch_size: int = 10, delay_between_batches: float = 1.0):
    """
    Send weekly email digest to all active subscribers.
    This function should be called by a scheduled job (cron).
    """
    from email_service import send_email

    print(f"[{datetime.now()}] Starting weekly digest...")

    supported_cities = CONFIG.get('SUPPORTED_LOCATIONS', [])

    for city in supported_cities:
        # Get active subscribers for this city
        subscribers = await get_active_subscribers(city)

        if not subscribers:
            print(f"[{datetime.now()}] No active subscribers for {city}")
            continue

        print(f"[{datetime.now()}] Sending digest to {len(subscribers)} subscribers for {city}")

        # Get events from database for the next 7 days
        from database import AsyncSessionLocal, Event
        from sqlalchemy import select
        from datetime import timedelta

        end_date = datetime.utcnow().date() + timedelta(days=7)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Event).where(
                    Event.city == city,
                    Event.date >= datetime.utcnow().date(),
                    Event.date <= end_date
                ).order_by(Event.date)
            )
            events = result.scalars().all()

        if not events:
            print(f"[{datetime.now()}] No events found for {city} in next 7 days")
            continue

        # Prepare email content
        city_name = CITY_MAPPING.get(city, {}).get('name', city)

        email_content = f"""
        <h2>Weekly Events in {city_name}</h2>
        <p>Here are the upcoming events for the next 7 days:</p>
        <ul>
        """

        for event in events[:20]:  # Limit to 20 events
            email_content += f"""
            <li>
                <strong>{event.title}</strong><br/>
                {event.date} @ {event.time}<br/>
                {event.location}
            </li>
            """

        email_content += "</ul>"

        # Process subscribers in batches to avoid overwhelming email service
        for i in range(0, len(subscribers), batch_size):
            batch = subscribers[i:i + batch_size]

            # Send emails in batch
            for subscriber in batch:
                try:
                    success = await send_email(
                        subscriber.email,
                        f"Weekly Events in {city_name}",
                        email_content
                    )

                    # Log the email send
                    from database import log_email_sent
                    await log_email_sent(
                        subscription_id=subscriber.id,
                        email=subscriber.email,
                        city=city,
                        events_count=len(events),
                        success=success
                    )

                    print(f"[{datetime.now()}] Sent digest to {subscriber.email}")

                except Exception as e:
                    print(f"[{datetime.now()}] Error sending to {subscriber.email}: {e}")
                    # Log the failure
                    from database import log_email_sent
                    await log_email_sent(
                        subscription_id=subscriber.id,
                        email=subscriber.email,
                        city=city,
                        events_count=len(events),
                        success=False,
                        error_message=str(e)
                    )

            # Delay between batches to avoid rate limiting
            if i + batch_size < len(subscribers):
                await asyncio.sleep(delay_between_batches)

        # Add delay between cities
        await asyncio.sleep(1)

    print(f"[{datetime.now()}] Weekly digest complete")


if __name__ == "__main__":
    # Test scraping for a single city
    import sys
    city = sys.argv[1] if len(sys.argv) > 1 else 'ca--los-angeles'
    asyncio.run(scrape_city_events(city))
