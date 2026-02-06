#!/usr/bin/env python3
"""
Test and validation script for db_sync integration
Verifies configuration, database connectivity, and data validation
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

from config_loader import get_config
from db_sync_enhanced import (
    DatabaseSyncManager,
    EventDataValidator,
    SupabaseSync,
    DeduplicationTracker
)


class SyncTester:
    """Test db_sync integration"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def log(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.tests.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        
        if passed:
            self.passed += 1
            print(f"  {status}: {test_name}")
        else:
            self.failed += 1
            print(f"  {status}: {test_name}")
            if message:
                print(f"         {message}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {percentage:.1f}%")
        print("=" * 70 + "\n")
        
        return self.failed == 0
    
    # ===== TEST METHODS =====
    
    def test_config_loading(self):
        """Test configuration loading"""
        print("\n[1] Configuration Loading")
        
        try:
            config = get_config()
            self.log("Config loads without error", True)
            
            # Check SYNC_MODE
            sync_mode = config.get('DATABASE.SYNC_MODE')
            self.log(f"DATABASE.SYNC_MODE exists (value: {sync_mode})", sync_mode is not None)
            
            # Check location
            location = config.get_location()
            self.log(f"Location loads (value: {location})", location is not None)
            
        except Exception as e:
            self.log("Config loading", False, str(e))
    
    def test_event_validation(self):
        """Test event data validation"""
        print("\n[2] Event Validation")
        
        # Valid event
        valid_event = {
            "title": "Test Concert",
            "date": "2026-02-15",
            "location": "Los Angeles, CA",
            "link": "https://example.com/event",
            "source": "Eventbrite",
            "price": 2500
        }
        
        is_valid, cleaned, errors = EventDataValidator.validate_event(valid_event)
        self.log("Valid event passes validation", is_valid, str(errors))
        
        if is_valid:
            self.log("Event has price_tier", 'price_tier' in cleaned)
            self.log("Event has category", 'category' in cleaned)
            self.log("Event has event_hash", 'event_hash' in cleaned)
            self.log("Price tier calculated correctly", cleaned.get('price_tier') == 2)
            self.log("Category auto-determined", cleaned.get('category') == 'Concert')
        
        # Invalid event (missing required field)
        invalid_event = {
            "title": "Test Event",
            # missing required fields
        }
        
        is_valid, cleaned, errors = EventDataValidator.validate_event(invalid_event)
        self.log("Invalid event fails validation", not is_valid)
        self.log("Errors are reported", len(errors) > 0)
    
    def test_price_tier_calculation(self):
        """Test price tier determination"""
        print("\n[3] Price Tier Calculation")
        
        test_cases = [
            (0, 0, "Free"),
            (1500, 1, "<$20"),
            (4500, 2, "<$50"),
            (7500, 3, "<$100"),
            (15000, 4, "$100+"),
        ]
        
        for price, expected_tier, label in test_cases:
            event = {"price": price}
            tier = EventDataValidator.determine_price_tier(event)
            self.log(f"Price {price} → Tier {expected_tier} ({label})", tier == expected_tier)
    
    def test_category_detection(self):
        """Test automatic category detection"""
        print("\n[4] Category Detection")
        
        test_cases = [
            ("Live Jazz Concert at Blue Note", "Concert"),
            ("Tech Startup Networking Meetup", "Networking"),
            ("Club Night - DJs and Dancing", "Nightlife"),
            ("Yoga Workshop for Beginners", "Workshop"),
            ("Food Tasting Event", "Food"),
        ]
        
        for title, expected_category in test_cases:
            event = {"title": title, "description": ""}
            category = EventDataValidator.categorize_event(event)
            self.log(
                f"'{title[:30]}...' → {expected_category}",
                category == expected_category,
                f"Got: {category}"
            )
    
    def test_event_hash_consistency(self):
        """Test event hash consistency"""
        print("\n[5] Event Hash Consistency")
        
        event = {
            "title": "Test Event",
            "date": "2026-02-15",
            "location": "Los Angeles",
            "source": "Eventbrite"
        }
        
        hash1 = EventDataValidator.generate_event_hash(event)
        hash2 = EventDataValidator.generate_event_hash(event)
        
        self.log("Same event generates same hash", hash1 == hash2)
        self.log("Hash is 32 characters", len(hash1) == 32)
        
        # Different event should have different hash
        event['title'] = "Different Event"
        hash3 = EventDataValidator.generate_event_hash(event)
        
        self.log("Different event generates different hash", hash1 != hash3)
    
    def test_deduplication_tracker(self):
        """Test deduplication tracker"""
        print("\n[6] Deduplication Tracker")
        
        tracker_file = "test_tracker.json"
        
        try:
            # Create tracker
            tracker = DeduplicationTracker(tracker_file)
            self.log("Tracker initializes", True)
            
            # Add events
            events = [
                {
                    "title": "Event 1",
                    "date": "2026-02-15",
                    "event_hash": "hash1"
                },
                {
                    "title": "Event 2",
                    "date": "2026-02-16",
                    "event_hash": "hash2"
                }
            ]
            
            tracker.add_events(events)
            self.log("Events added to tracker", True)
            
            # Check if tracked
            is_tracked = tracker.is_tracked("hash1")
            self.log("Tracked event is recognized", is_tracked)
            
            is_not_tracked = tracker.is_tracked("hash999")
            self.log("Non-tracked event is not recognized", not is_not_tracked)
            
            # Check stats
            stats = tracker.get_stats()
            self.log("Stats available", 'total_tracked' in stats)
            self.log("Total tracked correct", stats['total_tracked'] == 2)
            
            # Cleanup
            if os.path.exists(tracker_file):
                os.remove(tracker_file)
        
        except Exception as e:
            self.log("Deduplication tracker", False, str(e))
    
    async def test_supabase_config(self):
        """Test Supabase configuration"""
        print("\n[7] Supabase Configuration")
        
        try:
            sync = SupabaseSync()
            
            # Check if env vars are set
            url_set = os.environ.get('SUPABASE_URL') is not None
            key_set = os.environ.get('SUPABASE_KEY') is not None
            
            self.log("SUPABASE_URL env var is set", url_set)
            self.log("SUPABASE_KEY env var is set", key_set)
            
            # Check if client reports configured
            is_configured = sync.is_configured()
            self.log("Sync client reports configured", is_configured)
            
            if is_configured:
                self.log("Connection details available", True)
        
        except Exception as e:
            self.log("Supabase configuration", False, str(e))
    
    async def test_batch_validation(self):
        """Test batch event validation"""
        print("\n[8] Batch Validation")
        
        events = [
            {
                "title": "Event 1",
                "date": "2026-02-15",
                "location": "LA",
                "link": "https://example.com/1",
                "source": "Eventbrite"
            },
            {
                "title": "Event 2",
                "date": "2026-02-16",
                "location": "NY",
                "link": "https://example.com/2",
                "source": "Meetup"
            },
            {
                "title": "Event 3",
                # Invalid - missing required fields
            }
        ]
        
        valid, invalid, all_errors = EventDataValidator.validate_batch(events)
        
        self.log("Batch validation runs", True)
        self.log("Valid events counted correctly", len(valid) == 2)
        self.log("Invalid events detected", len(invalid) == 1)
        self.log("Errors are collected", len(all_errors) > 0)
    
    async def test_location_cleaning(self):
        """Test location cleaning (zero-width char removal)"""
        print("\n[9] Location Cleaning")
        
        # Location with zero-width spaces (from web scrapers)
        dirty_location = "\u200bBy Organization\u200bLos Angeles, CA"
        
        cleaned = EventDataValidator.clean_location(dirty_location)
        
        self.log("Zero-width chars removed", '\u200b' not in cleaned)
        self.log("Location is clean", cleaned == "By Organization Los Angeles, CA")
    
    async def test_email_validation(self):
        """Test email validation"""
        print("\n[10] Email Validation")
        
        test_cases = [
            ("user@example.com", True),
            ("test.email@company.co.uk", True),
            ("invalid@", False),
            ("@invalid.com", False),
            ("no-domain", False),
        ]
        
        for email, should_be_valid in test_cases:
            is_valid = SupabaseSync._validate_email(email)
            self.log(
                f"Email '{email}' valid={should_be_valid}",
                is_valid == should_be_valid
            )
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("RUNNING DATABASE SYNC VALIDATION TESTS")
        print("=" * 70)
        
        # Synchronous tests
        self.test_config_loading()
        self.test_event_validation()
        self.test_price_tier_calculation()
        self.test_category_detection()
        self.test_event_hash_consistency()
        self.test_deduplication_tracker()
        
        # Async tests
        await self.test_supabase_config()
        await self.test_batch_validation()
        await self.test_location_cleaning()
        await self.test_email_validation()
        
        return self.print_summary()


async def main():
    """Main entry point"""
    tester = SyncTester()
    all_passed = await tester.run_all_tests()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
