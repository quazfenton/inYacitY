#!/usr/bin/env python3
"""
Scheduled task script for rotating city scraping every 6 hours.
Each run scrapes:
  - 1 rotating city (cycles through all cities)
  - Up to 3 stale cities (last scrape > 5 days old)

With 42 cities, each city gets scraped roughly every 10.5 days via rotation,
plus stale catch-up ensures no city goes > 5 days without a scrape.

Can be run via cron: 0 */6 * * * /usr/bin/python3 /path/to/cron.py rotate
Or via APScheduler inside the backend process.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
import json
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from scraper_integration import (
    scrape_city_events,
    send_weekly_digest,
    get_next_city_to_scrape,
    get_stale_cities,
    get_all_scrape_info,
    record_scrape,
    refresh_all_cities
)
from database import get_active_subscribers, AsyncSessionLocal, Event
from sqlalchemy import select

# Define deterministic logs directory
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'cron_scraping.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def cleanup_old_events():
    """Remove events older than 30 days"""
    from database import Event
    from sqlalchemy import delete

    cutoff_date = datetime.utcnow().date() - timedelta(days=30)

    async with AsyncSessionLocal() as session:
        delete_stmt = delete(Event).where(Event.date < cutoff_date)
        result = await session.execute(delete_stmt)
        await session.commit()

        logger.info(f"Cleaned up {result.rowcount} events older than 30 days")


async def run_rotate_scrape():
    """Scrape 1 rotating city + up to 3 stale cities. Run every 6 hours."""
    logger.info("=" * 70)
    logger.info("ROTATING SCRAPE JOB STARTED")
    logger.info("=" * 70)

    cities_to_scrape = []

    # 1 rotating city
    rotating = get_next_city_to_scrape()
    if rotating:
        cities_to_scrape.append(rotating)
        logger.info(f"Rotating city: {rotating}")

    # Up to 3 stale cities (last scrape > 5 days)
    stale = get_stale_cities(max_count=3)
    for city in stale:
        if city not in cities_to_scrape:
            cities_to_scrape.append(city)

    if stale:
        logger.info(f"Stale cities (>5 days): {stale}")

    if not cities_to_scrape:
        logger.warning("No cities to scrape")
        return

    logger.info(f"Total cities to scrape: {len(cities_to_scrape)}")

    results = []
    for city in cities_to_scrape:
        try:
            logger.info(f"Scraping city: {city}")
            result = await scrape_city_events(city, source="cron")
            logger.info(f"  - Status: {result['status']}")
            logger.info(f"  - Events scraped: {result.get('events_scraped', 0)}")
            logger.info(f"  - Events saved: {result.get('events_saved', 0)}")
            results.append(result)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error scraping {city}: {e}")
            results.append({"city": city, "status": "error", "error": str(e)})

    # Save summary
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "job": "rotate_scrape",
        "cities_scraped": len(cities_to_scrape),
        "results": results,
        "status": "success"
    }

    summary_file = os.path.join(LOGS_DIR, 'last_scrape_summary.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Summary saved to {summary_file}")


async def run_full_scrape():
    """Scrape ALL cities. Run manually or weekly."""
    logger.info("=" * 70)
    logger.info("FULL SCRAPE JOB STARTED (all cities)")
    logger.info("=" * 70)

    try:
        scrape_results = await refresh_all_cities()

        logger.info(f"Scraping complete:")
        logger.info(f"  - Successful cities: {scrape_results['successful']}")
        logger.info(f"  - Failed cities: {scrape_results['failed']}")
        logger.info(f"  - Total events: {scrape_results['total_events']}")

        await cleanup_old_events()

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "job": "full_scrape",
            "scrape_results": scrape_results,
            "status": "success"
        }

        summary_file = os.path.join(LOGS_DIR, 'last_scrape_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Summary saved to {summary_file}")

    except Exception as e:
        logger.error(f"FULL SCRAPE JOB FAILED: {e}")

        error_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "job": "full_scrape",
            "error": str(e),
            "status": "failed"
        }

        summary_file = os.path.join(LOGS_DIR, 'last_scrape_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(error_summary, f, indent=2)

        raise


async def run_maintenance():
    """Cleanup old events + send weekly digest on Mondays."""
    logger.info("=" * 70)
    logger.info("MAINTENANCE JOB STARTED")
    logger.info("=" * 70)

    await cleanup_old_events()

    if datetime.utcnow().weekday() == 0:
        logger.info("Sending weekly digest (Monday)...")
        await send_weekly_digest()
        logger.info("Weekly digest sent")
    else:
        day_name = datetime.utcnow().strftime('%A')
        logger.info(f"Skipped weekly digest (today is {day_name}, not Monday)")

    logger.info("Maintenance complete")


async def run_status():
    """Print scrape status for all cities."""
    info = get_all_scrape_info()
    print(f"\n{'City':<30} {'Last Scraped':<25} {'Source':<10} {'Days':<6} {'Events':<8} {'Total':<8}")
    print("-" * 95)
    for city, data in sorted(info.items()):
        last = data.get('last_scraped', 'Never')[:19] if data.get('last_scraped') else 'Never'
        source = data.get('source', '-')
        days = f"{data.get('days_since_scrape', 'N/A')}"
        events = str(data.get('events_found', 0))
        total = str(data.get('total_scrapes', 0))
        print(f"{city:<30} {last:<25} {source:<10} {days:<6} {events:<8} {total:<8}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Nocturne Scheduled Tasks')
    parser.add_argument(
        'task',
        choices=['rotate', 'full', 'maintenance', 'status'],
        help='Task to run: rotate=1 city + stale (6hr), full=all cities, maintenance=cleanup+digest, status=show scrape times'
    )

    args = parser.parse_args()

    if args.task == 'rotate':
        asyncio.run(run_rotate_scrape())
    elif args.task == 'full':
        asyncio.run(run_full_scrape())
    elif args.task == 'maintenance':
        asyncio.run(run_maintenance())
    elif args.task == 'status':
        asyncio.run(run_status())
