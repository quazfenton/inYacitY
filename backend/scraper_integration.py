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

# Add scraper to path - handle different directory structures
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
scraper_dir = os.path.join(project_root, 'scraper')

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

# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Lock to prevent concurrent scraper runs that could interfere with each other
scraper_lock = asyncio.Lock()

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


async def scrape_city_events(city_id: str) -> Dict:
    """
    Scrape events for a specific city and save to database.
    Returns statistics about the scraping operation.
    """
    from scraper.run import run_all_scrapers
    import shutil

    logger.info(f"Starting scrape for city: {city_id}")

    # Load current config
    config = load_config()

    # Update config for this city
    config['LOCATION'] = city_id

    # Run the scrapers - use lock to prevent concurrent access to shared resources
    logger.info(f"Running scrapers for {city_id}...")

    # Change to scraper directory and run - protected by lock to prevent race conditions
    scraper_dir = os.path.join(os.path.dirname(__file__), '../scraper')
    original_dir = os.getcwd()

    async with scraper_lock:
        # Save temporary config (inside the lock to prevent race conditions)
        config_path = os.path.join(os.path.dirname(__file__), '../scraper/config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        try:
            os.chdir(scraper_dir)
            await run_all_scrapers()
        finally:
            os.chdir(original_dir)

        # Read the results while holding the lock
        all_events_file = os.path.join(scraper_dir, 'all_events.json')

        if not os.path.exists(all_events_file):
            logger.warning(f"No events found for {city_id}")
            return {
            "city_id": city_id,
            "status": "error",
            "message": "No events found",
            "events_count": 0
        }

    with open(all_events_file, 'r') as f:
        data = json.load(f)
        # Try to get events from the root level first
        events_data = data.get('events', [])
        
        # If no events at root, try to get from cities structure
        if not events_data and 'cities' in data:
            city_data = data['cities'].get(city_id, {})
            events_data = city_data.get('events', [])
            
            # Also check for events in all cities if specific city not found
            if not events_data:
                for city_key, city_info in data['cities'].items():
                    if isinstance(city_info, dict) and 'events' in city_info:
                        events_data.extend(city_info['events'])

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
    result = await save_events(events_data, city_id)

    logger.info(f"Saved {result['saved']} new events, updated {result['updated']} existing events")

    # Sync to Supabase if configured
    try:
        from supabase_integration import sync_events_to_supabase
        supabase_result = await sync_events_to_supabase(events_data, city_id)
        logger.info(f"Supabase sync result: {supabase_result}")
    except Exception as e:
        logger.warning(f"Supabase sync failed (non-critical): {e}")

    return {
        "city_id": city_id,
        "status": "success",
        "events_scraped": len(events_data),
        "events_saved": result['saved'],
        "events_updated": result['updated']
    }


async def refresh_all_cities() -> Dict:
    """
    Scrape events for all supported cities.
    Returns aggregated statistics.
    """
    from scraper.run import run_all_scrapers

    supported_cities = CONFIG.get('SUPPORTED_LOCATIONS', [])

    results = {
        "total_cities": len(supported_cities),
        "successful": 0,
        "failed": 0,
        "total_events": 0,
        "city_results": []
    }

    logger.info(f"Starting refresh of {len(supported_cities)} cities...")

    for city_id in supported_cities:
        try:
            result = await scrape_city_events(city_id)

            if result['status'] == 'success':
                results['successful'] += 1
                results['total_events'] += result.get('events_scraped', 0)
            else:
                results['failed'] += 1

            results['city_results'].append(result)

            # Add a small delay between cities to avoid rate limiting
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error scraping {city_id}: {e}")
            results['failed'] += 1
            results['city_results'].append({
                "city_id": city_id,
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

    for city_id in supported_cities:
        # Get active subscribers for this city
        subscribers = await get_active_subscribers(city_id)

        if not subscribers:
            print(f"[{datetime.now()}] No active subscribers for {city_id}")
            continue

        print(f"[{datetime.now()}] Sending digest to {len(subscribers)} subscribers for {city_id}")

        # Get events from database for the next 7 days
        from database import AsyncSessionLocal, Event
        from sqlalchemy import select
        from datetime import timedelta

        end_date = datetime.utcnow().date() + timedelta(days=7)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Event).where(
                    Event.city_id == city_id,
                    Event.date >= datetime.utcnow().date(),
                    Event.date <= end_date
                ).order_by(Event.date)
            )
            events = result.scalars().all()

        if not events:
            print(f"[{datetime.now()}] No events found for {city_id} in next 7 days")
            continue

        # Prepare email content
        city_name = CITY_MAPPING.get(city_id, {}).get('name', city_id)

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
                        city_id=city_id,
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
                        city_id=city_id,
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
