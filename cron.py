#!/usr/bin/env python3
"""
Scheduled task script for daily event scraping
This can be run via cron: 0 2 * * * /usr/bin/python3 /path/to/cron_scraper.py
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
import json
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from scraper_integration import refresh_all_cities, send_weekly_digest
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


async def run_daily_scrape():
    """Main daily scraping job"""
    logger.info("=" * 70)
    logger.info("DAILY SCRAPING JOB STARTED")
    logger.info("=" * 70)

    try:
        # Step 1: Refresh all cities
        logger.info("Step 1: Scraping all cities...")
        scrape_results = await refresh_all_cities()

        logger.info(f"Scraping complete:")
        logger.info(f"  - Successful cities: {scrape_results['successful']}")
        logger.info(f"  - Failed cities: {scrape_results['failed']}")
        logger.info(f"  - Total events: {scrape_results['total_events']}")

        # Step 2: Cleanup old events
        logger.info("\nStep 2: Cleaning up old events...")
        await cleanup_old_events()

        # Step 3: Send weekly digest (only on Monday)
        if datetime.utcnow().weekday() == 0:  # Monday is 0
            logger.info("\nStep 3: Sending weekly digest (Monday)...")
            await send_weekly_digest()
            logger.info("Weekly digest sent")
        else:
            day_name = datetime.utcnow().strftime('%A')
            logger.info(f"\nStep 3: Skipped weekly digest (today is {day_name}, not Monday)")

        logger.info("\n" + "=" * 70)
        logger.info("DAILY SCRAPING JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

        # Save results summary
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "scrape_results": scrape_results,
            "status": "success"
        }

        summary_file = os.path.join(LOGS_DIR, 'last_scrape_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Summary saved to {summary_file}")

    except Exception as e:
        logger.error(f"DAILY SCRAPING JOB FAILED: {e}")

        # Save error summary
        error_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "status": "failed"
        }

        summary_file = os.path.join(LOGS_DIR, 'last_scrape_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(error_summary, f, indent=2)

        # Re-raise to exit with error
        raise


async def send_test_digest():
    """Send a test digest for testing purposes"""
    logger.info("Sending test digest...")
    await send_weekly_digest()
    logger.info("Test digest sent")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Nocturne Scheduled Tasks')
    parser.add_argument(
        'task',
        choices=['daily', 'cleanup', 'digest'],
        help='Task to run: daily=full daily scrape, cleanup=clean old events, digest=send weekly digest'
    )

    args = parser.parse_args()

    if args.task == 'daily':
        asyncio.run(run_daily_scrape())
    elif args.task == 'cleanup':
        asyncio.run(cleanup_old_events())
        logger.info("Cleanup complete")
    elif args.task == 'digest':
        asyncio.run(send_test_digest())
