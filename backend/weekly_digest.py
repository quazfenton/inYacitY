#!/usr/bin/env python3
"""
Weekly Email Digest Script

Gathers upcoming events for each city and sends weekly digest emails
to subscribers with rate limiting and batching.

Usage:
    python weekly_digest.py --send                    # Send all digests
    python weekly_digest.py --send --city ca--los-angeles  # Send for specific city
    python weekly_digest.py --dry-run                 # Preview without sending
    python weekly_digest.py --days 7                  # Events for next 7 days
    python weekly_digest.py --test user@example.com   # Test send to single email

Schedule as cron job (weekly on Mondays at 9 AM):
    0 9 * * 1 cd /app && python backend/weekly_digest.py --send
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    get_upcoming_events,
    get_cities_with_active_subscribers,
    get_subscribers_by_city,
    get_future_events_for_city,
    log_email_sent,
    Subscription
)
from email_service import send_email, generate_email_template


@dataclass
class DigestResult:
    """Result of digest send operation"""
    city: str
    emails_sent: int
    emails_failed: int
    events_count: int
    errors: List[str]


class WeeklyDigestSender:
    """Manages sending weekly email digests to subscribers"""
    
    def __init__(
        self,
        days_ahead: int = 7,
        batch_size: int = 10,
        delay_between_batches: float = 1.0,
        max_events_per_email: int = 20
    ):
        self.days_ahead = days_ahead
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.max_events_per_email = max_events_per_email
        self.results: List[DigestResult] = []
    
    async def gather_events_for_city(self, city: str) -> List[Dict]:
        """
        Gather upcoming events for a city (this week only, no past events)
        Events are already sorted by date (ascending) from the database
        
        Args:
            city: City ID to gather events for
        
        Returns:
            List of event dictionaries (pre-sorted by date from database)
        """
        print(f"[GATHER] Fetching events for {city} (next {self.days_ahead} days)...")
        
        # get_future_events_for_city returns events already sorted by date from database
        # No additional sorting needed here
        events = await get_future_events_for_city(
            city=city,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=self.days_ahead),
            limit=self.max_events_per_email
        )
        
        # Convert to dictionaries (maintains database sort order)
        event_dicts = [event.to_dict() for event in events]
        
        print(f"[GATHER] Found {len(event_dicts)} upcoming events for {city} (sorted by date)")
        return event_dicts
    
    async def get_city_name(self, city: str) -> str:
        """
        Get display name for a city
        
        Args:
            city: City ID
        
        Returns:
            City display name
        """
        # Map city codes to names
        city_names = {
            'ca--los-angeles': 'Los Angeles',
            'ca--san-francisco': 'San Francisco',
            'ca--san-diego': 'San Diego',
            'co--denver': 'Denver',
            'dc--washington': 'Washington DC',
            'fl--miami': 'Miami',
            'ga--atlanta': 'Atlanta',
            'il--chicago': 'Chicago',
            'ma--boston': 'Boston',
            'nv--las-vegas': 'Las Vegas',
            'ny--new-york': 'New York',
            'pa--philadelphia': 'Philadelphia',
            'tx--austin': 'Austin',
            'tx--dallas': 'Dallas',
            'tx--houston': 'Houston',
            'ut--salt-lake-city': 'Salt Lake City',
            'wa--seattle': 'Seattle',
            'on--toronto': 'Toronto'
        }
        
        return city_names.get(city, city.replace('--', ' ').title())
    
    async def send_digest_to_subscriber(
        self,
        subscriber: Subscription,
        events: List[Dict],
        city_name: str,
        dry_run: bool = False
    ) -> bool:
        """
        Send weekly digest to a single subscriber
        
        Args:
            subscriber: Subscription object
            events: List of events to include
            city_name: Display name of city
            dry_run: If True, don't actually send
        
        Returns:
            True if sent successfully
        """
        if not events:
            print(f"  [SKIP] No events to send to {subscriber.email}")
            return False
        
        if dry_run:
            print(f"  [DRY-RUN] Would send {len(events)} events to {subscriber.email}")
            return True
        
        try:
            # Generate email content
            html_content = generate_email_template(city_name, events)
            
            # Send email
            subject = f"Your Weekly Nocturne Digest /// {city_name} /// {len(events)} Events"
            success = await send_email(
                to_email=subscriber.email,
                subject=subject,
                html_content=html_content
            )
            
            # Log the send attempt
            await log_email_sent(
                subscription_id=subscriber.id,
                email=subscriber.email,
                city=subscriber.city,
                events_count=len(events),
                success=success,
                error_message=None if success else "Failed to send email"
            )
            
            if success:
                print(f"  [SENT] Digest to {subscriber.email} ({len(events)} events)")
            else:
                print(f"  [FAILED] Could not send to {subscriber.email}")
            
            return success
            
        except Exception as e:
            print(f"  [ERROR] Failed to send to {subscriber.email}: {e}")
            
            # Log the error
            await log_email_sent(
                subscription_id=subscriber.id,
                email=subscriber.email,
                city=subscriber.city,
                events_count=len(events),
                success=False,
                error_message=str(e)
            )
            
            return False
    
    async def send_digest_for_city(
        self,
        city: str,
        dry_run: bool = False
    ) -> DigestResult:
        """
        Send weekly digest to all subscribers for a city
        
        Args:
            city: City ID
            dry_run: If True, preview without sending
        
        Returns:
            DigestResult with statistics
        """
        print(f"\n[PROCESSING] City: {city}")
        print("=" * 60)
        
        # Get city name
        city_name = await self.get_city_name(city)
        print(f"City Name: {city_name}")
        
        # Gather events
        events = await self.gather_events_for_city(city)
        
        if not events:
            print(f"[SKIP] No upcoming events for {city}")
            return DigestResult(
                city=city,
                emails_sent=0,
                emails_failed=0,
                events_count=0,
                errors=[]
            )
        
        # Get subscribers
        subscribers = await get_subscribers_by_city(city)
        
        if not subscribers:
            print(f"[SKIP] No active subscribers for {city}")
            return DigestResult(
                city=city,
                emails_sent=0,
                emails_failed=0,
                events_count=len(events),
                errors=[]
            )
        
        print(f"[INFO] Sending to {len(subscribers)} subscribers")
        
        # Send emails in batches with rate limiting
        sent_count = 0
        failed_count = 0
        errors = []
        
        for i in range(0, len(subscribers), self.batch_size):
            batch = subscribers[i:i + self.batch_size]
            print(f"\n[BATCH] Sending batch {i//self.batch_size + 1}/{(len(subscribers) + self.batch_size - 1)//self.batch_size}")
            
            # Send to each subscriber in batch concurrently
            tasks = [
                self.send_digest_to_subscriber(sub, events, city_name, dry_run)
                for sub in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                    errors.append(str(result))
                elif result:
                    sent_count += 1
                else:
                    failed_count += 1
            
            # Delay between batches (rate limiting)
            if i + self.batch_size < len(subscribers) and not dry_run:
                print(f"  [RATE-LIMIT] Waiting {self.delay_between_batches}s before next batch...")
                await asyncio.sleep(self.delay_between_batches)
        
        result = DigestResult(
            city=city,
            emails_sent=sent_count,
            emails_failed=failed_count,
            events_count=len(events),
            errors=errors
        )
        
        print(f"\n[RESULT] {city}:")
        print(f"  Emails sent: {sent_count}")
        print(f"  Emails failed: {failed_count}")
        print(f"  Events included: {len(events)}")
        
        return result
    
    async def send_all_digests(
        self,
        specific_city: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Send weekly digests for all cities with subscribers
        
        Args:
            specific_city: Optional city to limit to just that city
            dry_run: If True, preview without sending
        """
        print("\n" + "=" * 60)
        print("WEEKLY EMAIL DIGEST")
        print("=" * 60)
        print(f"Mode: {'DRY-RUN (preview only)' if dry_run else 'LIVE (sending emails)'}")
        print(f"Days ahead: {self.days_ahead}")
        print(f"Batch size: {self.batch_size}")
        print(f"Delay between batches: {self.delay_between_batches}s")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # Get cities with subscribers
        if specific_city:
            cities = [specific_city]
            print(f"\n[MODE] Processing single city: {specific_city}")
        else:
            cities = await get_cities_with_active_subscribers()
            print(f"\n[INFO] Found {len(cities)} cities with active subscribers")
        
        # Process each city
        for city in cities:
            result = await self.send_digest_for_city(city, dry_run)
            self.results.append(result)
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        total_sent = sum(r.emails_sent for r in self.results)
        total_failed = sum(r.emails_failed for r in self.results)
        total_events = sum(r.events_count for r in self.results)
        
        print("\n" + "=" * 60)
        print("DIGEST COMPLETE")
        print("=" * 60)
        print(f"Total cities processed: {len(self.results)}")
        print(f"Total emails sent: {total_sent}")
        print(f"Total emails failed: {total_failed}")
        print(f"Total events included: {total_events}")
        print(f"Duration: {duration:.1f} seconds")
        print("=" * 60)
    
    async def test_send(self, test_email: str, city: Optional[str] = None):
        """
        Send a test digest to a single email address
        
        Args:
            test_email: Email address to send test to
            city: Optional specific city, or uses first available
        """
        print(f"\n[TEST MODE] Sending test digest to {test_email}")
        
        # Determine city
        if not city:
            cities = await get_cities_with_active_subscribers()
            if not cities:
                print("[ERROR] No cities with subscribers found")
                return
            city = cities[0]
        
        # Get city name and events
        city_name = await self.get_city_name(city)
        events = await self.gather_events_for_city(city)
        
        if not events:
            print(f"[ERROR] No events found for {city}")
            return
        
        # Create mock subscriber
        mock_subscriber = Subscription(
            id=0,
            email=test_email,
            city=city,
            is_active=True
        )
        
        # Send test email
        success = await self.send_digest_to_subscriber(
            mock_subscriber,
            events,
            city_name,
            dry_run=False
        )
        
        if success:
            print(f"\n[TEST SUCCESS] Digest sent to {test_email}")
            print(f"City: {city_name}")
            print(f"Events: {len(events)}")
        else:
            print(f"\n[TEST FAILED] Could not send to {test_email}")


async def main():
    parser = argparse.ArgumentParser(
        description='Weekly Email Digest Sender',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Send all weekly digests
    python weekly_digest.py --send
    
    # Preview without sending (dry run)
    python weekly_digest.py --dry-run
    
    # Send for specific city only
    python weekly_digest.py --send --city ca--los-angeles
    
    # Send for next 14 days instead of 7
    python weekly_digest.py --send --days 14
    
    # Test send to single email
    python weekly_digest.py --test user@example.com
    
    # Test for specific city
    python weekly_digest.py --test user@example.com --city ny--new-york
    
    # Custom batch size and delay (for rate limiting)
    python weekly_digest.py --send --batch-size 5 --delay 2.0
        """
    )
    
    parser.add_argument('--send', action='store_true',
                       help='Send digests (required for actual sending)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without sending emails')
    parser.add_argument('--city',
                       help='Process only specific city')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days ahead to include events (default: 7)')
    parser.add_argument('--test',
                       help='Send test digest to specific email address')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Emails per batch (default: 10)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Seconds between batches (default: 1.0)')
    parser.add_argument('--max-events', type=int, default=20,
                       help='Max events per email (default: 20)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.send and not args.dry_run and not args.test:
        print("[ERROR] Must specify one of: --send, --dry-run, or --test")
        parser.print_help()
        return
    
    # Initialize sender
    sender = WeeklyDigestSender(
        days_ahead=args.days,
        batch_size=args.batch_size,
        delay_between_batches=args.delay,
        max_events_per_email=args.max_events
    )
    
    # Execute
    if args.test:
        await sender.test_send(args.test, args.city)
    else:
        await sender.send_all_digests(
            specific_city=args.city,
            dry_run=args.dry_run
        )


if __name__ == "__main__":
    asyncio.run(main())
