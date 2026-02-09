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


def normalize_iso(dt_str: str) -> str:
    if not dt_str:
        return ""
    return re.sub(r'\[.*\]$', '', dt_str)


def parse_iso_datetime(dt_str: str) -> tuple:
    """Parse ISO datetime to (date, time)."""
    if not dt_str:
        return ("", "")
    try:
        cleaned = normalize_iso(dt_str.replace('Z', '+00:00'))
        dt = datetime.fromisoformat(cleaned)
        return (dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p").lstrip('0'))
    except ValueError:
        return ("", "")


def parse_date_time_text(text: str) -> tuple:
    if not text:
        return ("", "")
    # e.g., "Saturday, Feb 28, 6:15 PM to Saturday, Feb 28, 9:15 PM PST"
    date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})', text)
    time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text, re.I)
    if date_match:
        month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                     'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
        month = month_map.get(date_match.group(1))
        day = int(date_match.group(2))
        year = datetime.now().year
        try:
            d = datetime(year, month, day)
            if d < datetime.now():
                d = datetime(year + 1, month, day)
            date_val = d.strftime("%Y-%m-%d")
        except ValueError:
            date_val = ""
    else:
        date_val = ""

    time_val = time_match.group(1).upper().replace(' ', '') if time_match else ""
    return (date_val, time_val)


async def fetch_meetup_details(url: str) -> dict:
    """Fetch location and time from individual Meetup event page."""
    html = await fetch_page(url, use_firecrawl_fallback=True)
    if not html:
        return {}
    soup = BeautifulSoup(html, 'html.parser')
    details = {}

    time_elem = soup.find('time', class_=re.compile(r'block', re.I)) or soup.find('time')
    if time_elem:
        dt_attr = time_elem.get('datetime')
        if dt_attr:
            date_val, time_val = parse_iso_datetime(dt_attr)
            if date_val:
                details['date'] = date_val
            if time_val:
                details['time'] = time_val
        else:
            date_val, time_val = parse_date_time_text(time_elem.get_text(strip=True))
            if date_val:
                details['date'] = date_val
            if time_val:
                details['time'] = time_val

    loc_elem = soup.find('p', class_=re.compile(r'text-ds2-text-fill-tertiary-enabled', re.I))
    if loc_elem:
        details['location'] = loc_elem.get_text(strip=True)

    return details


async def scrape_meetup(location: str = None) -> list:
    """Scrape Meetup events"""
    config = get_config()

    city_code = None
    if not location:
        # Convert location format from config to Meetup format
        city_code = config.get_location()
        if '--' in city_code:
            parts = city_code.split('--')
            location = f"us--{parts[0]}--{parts[1]}"
        else:
            location = f"us--{city_code}"
    else:
        city_code = location

    output_file = os.path.join(os.path.dirname(__file__), "meetup_events.json")

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
                    date_val, time_val = parse_iso_datetime(item.get('startDate', ''))
                    event = {
                        'title': item.get('name', 'Unknown'),
                        'link': item.get('url', ''),
                        'date': date_val,
                        'time': time_val,
                        'location': item.get('location', {}).get('name', 'Location TBA'),
                        'description': item.get('description', '')[:200],
                        'source': 'Meetup',
                        'city': city_code
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

        for link in event_links[:40]:
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

                # Try to parse time/date from nearby time tag
                parent = link.find_parent(['div', 'li', 'article'])
                date_val = ""
                time_val = ""
                if parent:
                    time_elem = parent.find('time')
                    if time_elem:
                        dt_attr = time_elem.get('datetime')
                        if dt_attr:
                            date_val, time_val = parse_iso_datetime(dt_attr)
                        else:
                            date_val, time_val = parse_date_time_text(time_elem.get_text(strip=True))

                events.append({
                    'title': title,
                    'link': href,
                    'date': date_val,
                    'time': time_val,
                    'location': 'Location TBA',
                    'description': '',
                    'source': 'Meetup',
                    'city': city_code
                })
            except:
                pass

        print(f"Found {len(events)} events from HTML parsing")

    # Enrich with individual event pages when missing time/location
    for event in events:
        if not event.get('date') or not event.get('time') or event.get('location') == "Location TBA":
            details = await fetch_meetup_details(event['link'])
            if details.get('date') and not event.get('date'):
                event['date'] = details['date']
            if details.get('time') and not event.get('time'):
                event['time'] = details['time']
            if details.get('location') and event.get('location') == "Location TBA":
                event['location'] = details['location']
        await asyncio.sleep(0.3)

    # Save results (city-scoped)
    out_data = {'cities': {}, 'last_updated': datetime.now().isoformat()}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing = json.load(f)
                if isinstance(existing, dict) and existing.get('cities'):
                    out_data['cities'] = existing['cities']
        except:
            pass

    out_data['cities'][city_code] = {
        'events': events,
        'total': len(events),
        'last_updated': datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(out_data, f, indent=2)

    print(f"✓ Saved {len(events)} events to {output_file}")
    return events


async def main():
    events = await scrape_meetup("us--ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e.get('date', 'TBA')}")


if __name__ == '__main__':
    asyncio.run(main())

