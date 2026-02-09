#!/usr/bin/env python3
"""
RA.co scraper - Playwright primary, Firecrawl fallback
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from browser import fetch_page
from playwright.async_api import async_playwright


# City mapping
RA_CITIES = {
    'ca--los-angeles': ('us', 'losangeles'),
    'ny--new-york': ('us', 'newyorkcity'),
    'fl--miami': ('us', 'miami'),
    'il--chicago': ('us', 'chicago'),
    'tx--austin': ('us', 'austin'),
    'ca--san-francisco': ('us', 'sanfrancisco'),
    'wa--seattle': ('us', 'seattle'),
    'co--denver': ('us', 'denver'),
    'ma--boston': ('us', 'boston'),
}


async def scrape_ra(location: str = "ca--los-angeles") -> list:
    """Scrape RA.co events for a location"""
    output_file = "ra_events.json"
    
    # Convert location code
    parts = location.split('--')
    if len(parts) >= 2:
        city = parts[1].replace('-', '')
    else:
        city = 'losangeles'
    
    url = f"https://ra.co/events/us/{city}"
    print(f"\nScraping RA.co: {url}")
    
    # Use mobile user agent to bypass DataDome
    browser = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        
        # Create mobile context to avoid detection
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            viewport={'width': 375, 'height': 812},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        
        page = await context.new_page()
        
        # Navigate with longer timeout
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        
        html = await page.content()
        await browser.close()
        await p.stop()
        
        if len(html) < 5000:
            print(f"Page too small ({len(html)} bytes), likely blocked")
            return []
        
    except Exception as e:
        print(f"Error: {e}")
        if browser:
            await browser.close()
        return []
    
    # Parse events
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # Find events by data-testid
    event_cards = soup.find_all(attrs={'data-pw-test-id': 'event-title'})
    print(f"Found {len(event_cards)} events with data-pw-test-id")
    
    for card in event_cards:
        try:
            link_elem = card.find('a')
            if not link_elem:
                continue
            
            href = link_elem.get('href', '')
            if not href:
                continue
            
            if not href.startswith('http'):
                href = f"https://ra.co{href}"
            
            title = link_elem.get_text(strip=True)
            
            events.append({
                'title': title,
                'date': 'TBA',
                'time': 'TBA',
                'location': 'TBA',
                'link': href,
                'description': '',
                'source': 'RA.co',
                'city': location
            })
            
        except Exception as e:
            print(f"Error parsing card: {e}")
            continue
    
    print(f"Extracted {len(events)} events")
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump({
            'events': events,
            'total': len(events),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"✓ Saved {len(events)} events to {output_file}")
    return events


async def main():
    events = await scrape_ra("ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['link'][:50]}")


if __name__ == '__main__':
    asyncio.run(main())
