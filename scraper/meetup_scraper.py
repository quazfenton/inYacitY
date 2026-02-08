#!/usr/bin/env python3
"""
Meetup scraper - Playwright primary, Firecrawl fallback
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from browser import fetch_page
from config_loader import get_config


async def scrape_meetup(location: str = None) -> list:
    """Scrape Meetup events"""
    config = get_config()
    fetch_details = config.get_scraper_config('MEETUP').get('fetch_details', True)
    
    if not location:
        # Convert location format from config to Meetup format
        city_code = config.get_location()
        if '--' in city_code:
            parts = city_code.split('--')
            location = f"us--{parts[0]}--{parts[1]}"
        else:
            location = f"us--{city_code}"
    
    output_file = "meetup_events.json"
    
    # Build URL
    url = f"https://www.meetup.com/find/?location={location}&source=EVENTS"
    print(f"\nScraping Meetup: {url}")
    
    # Fetch page
    html = await fetch_page(url, use_firecrawl_fallback=True)
    if not html:
        print("Failed to fetch Meetup page")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # Method 1: JSON-LD structured data
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            for item in items:
                if item.get('@type') == 'Event':
                    date, time = _parse_iso_datetime(item.get('startDate', ''))
                    event = {
                        'title': item.get('name', 'Unknown'),
                        'link': item.get('url', ''),
                        'date': date,
                        'time': time,
                        'location': item.get('location', {}).get('name', 'Location TBA'),
                        'description': item.get('description', '')[:200],
                        'source': 'Meetup'
                    }
                    if event['link'] and event not in events:
                        events.append(event)
        except:
            pass
    
    print(f"Found {len(events)} events from JSON-LD")
    
    # Method 2: Parse event cards if JSON-LD didn't work well
    if len(events) < 5:
        # Find event links
        event_links = soup.find_all('a', href=re.compile(r'/events/\w+'))
        
        for link in event_links[:20]:  # Limit to 20
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                # Clean URL
                if href.startswith('/'):
                    href = f"https://www.meetup.com{href}"
                href = href.split('?')[0]
                
                # Skip duplicates
                if any(e['link'] == href for e in events):
                    continue
                
                # Get title
                title = link.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                
                # Clean title
                title = re.sub(r'\d+\.?\d*\s*(attendees|going|members)', '', title, flags=re.I)
                title = re.sub(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d+', '', title)
                title = title.strip(' ·•')
                
                if not title:
                    continue
                
                events.append({
                    'title': title,
                    'link': href,
                    'date': '',
                    'time': '',
                    'location': 'Location TBA',
                    'description': '',
                    'source': 'Meetup'
                })
            except:
                pass
        
        print(f"Found {len(events)} events from HTML parsing")
    
    # Fetch detail pages for missing fields
    for event in events:
        if fetch_details and (not event.get('date') or not event.get('time') or event.get('location') == 'Location TBA'):
            details = await _fetch_meetup_details(event.get('link', ''))
            event.update({k: v for k, v in details.items() if v})
        event.setdefault('city', config.get_location())

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
    events = await scrape_meetup("us--ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e.get('date', 'TBA')}")


if __name__ == '__main__':
    asyncio.run(main())
def _parse_iso_datetime(value: str) -> tuple:
    if not value:
        return ("", "")
    cleaned = re.sub(r'\[.*?\]', '', value)
    try:
        dt = datetime.fromisoformat(cleaned)
        return (dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip("0"))
    except Exception:
        return ("", "")


async def _fetch_meetup_details(url: str) -> dict:
    details = {}
    try:
        html = await fetch_page(url, use_firecrawl_fallback=True)
        if not html:
            return details
        soup = BeautifulSoup(html, 'html.parser')
        time_elem = soup.find('time')
        if time_elem and time_elem.get('datetime'):
            date, time = _parse_iso_datetime(time_elem.get('datetime', ''))
            if date:
                details['date'] = date
            if time:
                details['time'] = time
        if time_elem and not details.get('time'):
            text = time_elem.get_text(" ", strip=True)
            match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text, re.I)
            if match:
                details['time'] = match.group(1).upper()

        location_elem = soup.find('p', class_=re.compile(r'ds2-r16', re.I))
        if location_elem:
            details['location'] = location_elem.get_text(" ", strip=True)
    except Exception:
        return details
    return details
