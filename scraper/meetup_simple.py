#!/usr/bin/env python3
"""
Simple Meetup scraper using JSON-LD extraction
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def scrape_meetup_simple(location_code: str, output_file: str = "meetup_events.json"):
    """Scrape Meetup events using JSON-LD data"""
    url = f"https://www.meetup.com/find/?location={location_code}&source=EVENTS"
    
    events = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)  # Wait for JS to load
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract JSON-LD event data
            script_tags = soup.find_all('script', type='application/ld+json')
            print(f"Found {len(script_tags)} JSON-LD scripts")
            
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    
                    # Handle both single events and arrays
                    if isinstance(data, dict) and data.get('@type') == 'Event':
                        events.append(parse_meetup_event(data))
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Event':
                                events.append(parse_meetup_event(item))
                                
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            print(f"Found {len(events)} events")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()
    
    # Save events
    with open(output_file, 'w') as f:
        json.dump({'events': events, 'total': len(events)}, f, indent=2, default=str)
    
    print(f"Saved {len(events)} events to {output_file}")
    return events


def parse_meetup_event(data: dict) -> dict:
    """Parse a Meetup event from JSON-LD data"""
    # Parse date
    start_date = data.get('startDate', '')
    date_str = "TBA"
    time_str = "TBA"
    
    if start_date:
        try:
            # Handle ISO format
            dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%I:%M %p")
        except:
            date_str = start_date[:10] if len(start_date) >= 10 else "TBA"
    
    # Get location
    location_data = data.get('location', {})
    if isinstance(location_data, dict):
        if location_data.get('@type') == 'VirtualLocation':
            location = "Online"
        else:
            place_name = location_data.get('name', '')
            address_data = location_data.get('address', {})
            if isinstance(address_data, dict):
                city = address_data.get('addressLocality', '')
                state = address_data.get('addressRegion', '')
                street = address_data.get('streetAddress', '')
                location_parts = [p for p in [place_name, street, city, state] if p]
                location = ', '.join(location_parts) if location_parts else "Location TBA"
            else:
                location = place_name or "Location TBA"
    else:
        location = "Location TBA"
    
    # Get organizer
    organizer = data.get('organizer', {})
    organizer_name = organizer.get('name', '') if isinstance(organizer, dict) else ''
    
    return {
        'title': data.get('name', 'Unknown Event'),
        'date': date_str,
        'time': time_str,
        'location': location,
        'link': data.get('url', ''),
        'description': data.get('description', 'Description not available')[:300],
        'source': 'Meetup',
        'city': location_code,
        'organizer': organizer_name
    }


async def main():
    # Load config
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except:
            pass
    
    location = config.get('LOCATION', 'ca--los-angeles')
    
    # Convert location format
    if '--' in location:
        parts = location.split('--')
        if len(parts) >= 2:
            meetup_location = f"us--{parts[0]}--{parts[1]}"
        else:
            meetup_location = location
    else:
        meetup_location = f"us--{location}"
    
    await scrape_meetup_simple(meetup_location)


if __name__ == '__main__':
    import os
    asyncio.run(main())
