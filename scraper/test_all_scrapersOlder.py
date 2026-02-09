#!/usr/bin/env python3
"""
Test script to verify all scrapers work correctly
Tests Eventbrite, Meetup, and Luma individually
"""

import asyncio
import json
import sys
from datetime import datetime


async def test_eventbrite():
    """Test Eventbrite scraper"""
    print("\n" + "=" * 70)
    print("TESTING EVENTBRITE SCRAPER")
    print("=" * 70)
    
    try:
        from scrapeevents import scrape_eventbrite_page
        
        # Test URL for LA free events
        test_url = "https://www.eventbrite.com/d/ca--los-angeles/free--events/?page=1"
        print(f"Testing URL: {test_url}")
        
        events = await scrape_eventbrite_page(test_url, existing_links=set())
        
        print(f"✓ Eventbrite scraper working!")
        print(f"  Found {len(events)} events")
        
        if events:
            print(f"\n  Sample event:")
            event = events[0]
            print(f"    Title: {event.get('title', 'N/A')[:60]}")
            print(f"    Date: {event.get('date', 'N/A')}")
            print(f"    Time: {event.get('time', 'N/A')}")
            print(f"    Location: {event.get('location', 'N/A')[:60]}")
            print(f"    Source: {event.get('source', 'N/A')}")
        
        return len(events) > 0
    
    except Exception as e:
        print(f"✗ Eventbrite scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_meetup():
    """Test Meetup scraper"""
    print("\n" + "=" * 70)
    print("TESTING MEETUP SCRAPER")
    print("=" * 70)
    
    try:
        from scrapeevents import scrape_meetup_events
        
        # Test location: Los Angeles
        test_location = "us--ca--los-angeles"
        print(f"Testing location: {test_location}")
        
        events = await scrape_meetup_events(test_location, search_terms=[], filters=[])
        
        print(f"✓ Meetup scraper working!")
        print(f"  Found {len(events)} events")
        
        if events:
            print(f"\n  Sample event:")
            event = events[0]
            print(f"    Title: {event.get('title', 'N/A')[:60]}")
            print(f"    Date: {event.get('date', 'N/A')}")
            print(f"    Time: {event.get('time', 'N/A')}")
            print(f"    Location: {event.get('location', 'N/A')[:60]}")
            print(f"    Source: {event.get('source', 'N/A')}")
        
        return len(events) > 0
    
    except Exception as e:
        print(f"✗ Meetup scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_luma():
    """Test Luma scraper"""
    print("\n" + "=" * 70)
    print("TESTING LUMA SCRAPER")
    print("=" * 70)
    
    try:
        from scrapeevents import scrape_luma_events
        
        # Test city: LA
        test_city = "la"
        print(f"Testing city: {test_city}")
        
        events = await scrape_luma_events(test_city)
        
        print(f"✓ Luma scraper working!")
        print(f"  Found {len(events)} events")
        
        if events:
            print(f"\n  Sample event:")
            event = events[0]
            print(f"    Title: {event.get('title', 'N/A')[:60]}")
            print(f"    Date: {event.get('date', 'N/A')}")
            print(f"    Time: {event.get('time', 'N/A')}")
            print(f"    Location: {event.get('location', 'N/A')[:60]}")
            print(f"    Source: {event.get('source', 'N/A')}")
        
        return len(events) > 0
    
    except Exception as e:
        print(f"✗ Luma scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 70)
    print("SCRAPER DIAGNOSTICS - Testing all 3 sources")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    
    results = {}
    
    # Test each scraper
    results['eventbrite'] = await test_eventbrite()
    results['meetup'] = await test_meetup()
    results['luma'] = await test_luma()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for scraper, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{scraper:15} {status}")
    
    all_pass = all(results.values())
    print(f"\n{'Overall':15} {'✓ ALL PASS' if all_pass else '✗ SOME FAILED'}")
    
    if all_pass:
        print("\n✓ All scrapers are working correctly!")
        return 0
    else:
        print("\n✗ Some scrapers are not working. Check errors above.")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
