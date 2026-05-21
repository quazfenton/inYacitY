"""
APScheduler-based local cron replacement.
Runs inside the FastAPI process - no n8n or external cron needed.

Jobs:
- rotate_scrape: Every 6 hours, scrapes 1 rotating city + up to 3 stale cities (>5 days old)
- maintenance: Daily at 2 AM UTC, cleans old events + sends weekly digest on Mondays
"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def job_rotate_scrape():
    """Scrape 1 rotating city + up to 3 stale cities (>5 days). Runs every 6 hours."""
    try:
        from scraper_integration import scrape_city_events, get_next_city_to_scrape, get_stale_cities

        all_cities = []

        # 1 rotating city
        rotating = get_next_city_to_scrape()
        if rotating:
            all_cities.append(rotating)

        # Up to 3 stale cities (last scrape > 5 days)
        stale = get_stale_cities(max_count=3)
        for city in stale:
            if city not in all_cities:
                all_cities.append(city)

        if not all_cities:
            logger.warning("[scheduler] No cities to scrape")
            return

        logger.info(f"[scheduler] Rotating scrape: {len(all_cities)} cities - {all_cities}")

        for city in all_cities:
            try:
                result = await scrape_city_events(city, source="cron")
                logger.info(f"[scheduler] Scrape complete for {city}: {result.get('events_scraped', 0)} events")
            except Exception as e:
                logger.error(f"[scheduler] Scrape failed for {city}: {e}")

            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"[scheduler] Rotate scrape failed: {e}")


async def job_maintenance():
    """Daily maintenance: cleanup old events + weekly digest on Mondays."""
    try:
        from scraper_integration import send_weekly_digest
        from datetime import datetime, timedelta
        from database import AsyncSessionLocal, Event
        from sqlalchemy import delete

        logger.info("[scheduler] Running daily maintenance")

        cutoff_date = datetime.utcnow().date() - timedelta(days=30)
        async with AsyncSessionLocal() as session:
            result = await session.execute(delete(Event).where(Event.date < cutoff_date))
            await session.commit()
            logger.info(f"[scheduler] Cleaned up {result.rowcount} old events")

        if datetime.utcnow().weekday() == 0:
            logger.info("[scheduler] Sending weekly digest")
            await send_weekly_digest()
            logger.info("[scheduler] Weekly digest sent")

    except Exception as e:
        logger.error(f"[scheduler] Maintenance failed: {e}")


def start_scheduler():
    """Start the scheduler with all jobs."""
    scheduler.add_job(
        job_rotate_scrape,
        trigger=IntervalTrigger(hours=6),
        id="rotate_scrape",
        name="Rotate city scrape + stale catch-up (every 6 hours)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600
    )

    scheduler.add_job(
        job_maintenance,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="daily_maintenance",
        name="Daily maintenance (cleanup + weekly digest)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=7200
    )

    scheduler.start()
    logger.info("[scheduler] Started - rotate_scrape (6hr + stale catch-up), daily_maintenance (2AM UTC)")


def stop_scheduler():
    """Shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped")
