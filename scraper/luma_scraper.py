#!/usr/bin/env python3
"""
Luma scraper - Playwright primary, Firecrawl fallback
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from browser import fetch_page, create_browser, close_browser
from typing import Optional
from config_loader import get_config


async def fetch_luma_page(url: str) -> Optional[str]:
    """Fetch Luma page with retry logic"""
    browser = None
    try:
        browser, page = await create_browser(headless=True)

        # Try networkidle with longer timeout
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except:
            # Fallback to domcontentloaded if networkidle times out
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        await asyncio.sleep(2)
        html = await page.content()
        await close_browser(browser)
        return html
    except Exception as e:
        if browser:
            await close_browser(browser)
        raise e


def clean_luma_location(text: str) -> str:
    """Clean Luma location text and remove organizer prefixes."""
    if not text:
        return "Location TBA"
    cleaned = text.replace('\u200b', ' ')
    cleaned = ' '.join(cleaned.split())
    if "By " in cleaned:
        cleaned = cleaned.split("By ", 1)[1].strip()
    # Prefer address-like segment if present
    addr_match = re.search(r'(\d{1,5}\s+\S.*)', cleaned)
    if addr_match:
        return addr_match.group(1).strip()
    for sep in ['·', '|', '•', '—', '-']:
        if sep in cleaned:
            return cleaned.split(sep)[-1].strip()
    return cleaned or "Location TBA"


async def fetch_luma_details(url: str) -> dict:
    """Fetch description and improved location from Luma event page."""
    html = await fetch_page(url, use_firecrawl_fallback=True)
    if not html:
        return {}
    soup = BeautifulSoup(html, 'html.parser')
    details = {}

    desc_elem = soup.select_one('div.content-card.event-about-card .spark-content') or soup.select_one('.spark-content')
    if desc_elem:
        details['description'] = desc_elem.get_text(" ", strip=True)[:500]

    loc_elem = soup.select_one('[data-testid="event-venue"]')
    if loc_elem:
        details['location'] = clean_luma_location(loc_elem.get_text(strip=True))

    time_elem = soup.find('time')
    if time_elem and time_elem.get('datetime'):
        details['datetime'] = time_elem.get('datetime')

    return details


async def scrape_luma(city: str = None) -> list:
    """Scrape Luma events for a city"""
    config = get_config()

    luma_config = config.get_scraper_config('LUMA')
    luma_map = luma_config.get('location_map', {})

    city_code = None
    if not city:
        location = config.get_location()
        city_code = location
        city = luma_map.get(location)
        if not city:
            print(f"⚠ Luma: City '{location}' not supported. Skipping.")
            return []
    elif '--' in city:
        city_code = city
        city = luma_map.get(city)
        if not city:
            print(f"⚠ Luma: City '{city_code}' not supported. Skipping.")
            return []
    else:
        city_code = city

    output_file = os.path.join(os.path.dirname(__file__), "luma_events.json")

    url = f"https://lu.ma/{city}"
    print(f"\nScraping Luma: {url}")

    # Fetch page
    html = await fetch_luma_page(url)
    if not html:
        print("Failed to fetch Luma page")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    events = []

    # Find all content cards directly
    cards = soup.find_all('div', class_='content-card')
    print(f"Found {len(cards)} event cards")

    for card in cards:
        try:
            # Get event link - handle query params
            link_elem = card.find('a', href=re.compile(r'/[a-z0-9]+'))
            if not link_elem:
                continue

            href = link_elem.get('href', '')
            event_id = href.strip('/').split('?')[0]
            event_url = f"https://lu.ma/{event_id}"

            # Get title
            h3 = card.find('h3')
            title = h3.get_text(strip=True) if h3 else "Unknown Event"

            # Get date from parent context or card text
            card_text = card.get_text()

            # Try to find date in nearby date header
            date_str = datetime.now().strftime("%Y-%m-%d")
            prev = card.find_previous('div', class_='date-title')
            if prev:
                date_elem = prev.find('div', class_='date')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_text)
                    day_match = re.search(r'(\d{1,2})', date_text)
                    if month_match and day_match:
                        month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                     'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                        month = month_map.get(month_match.group(1), 1)
                        day = int(day_match.group(1))
                        year = datetime.now().year
                        event_date = datetime(year, month, day)
                        if event_date < datetime.now():
                            event_date = datetime(year + 1, month, day)
                        date_str = event_date.strftime("%Y-%m-%d")

            # Get time
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)', card_text)
            time_str = time_match.group(1) if time_match else "TBA"

            # Get location
            location = "Location TBA"
            for elem in card.find_all(['div', 'span']):
                text = elem.get_text(strip=True)
                if len(text) > 3 and len(text) < 100 and not re.search(r'\b(?:am|pm|min|hour)\b|\d+(?:am|pm)', text, re.IGNORECASE):
                    if not elem.find('h3') and not elem.find('a'):
                        location = clean_luma_location(text)
                        break

            events.append({
                'title': title,
                'date': date_str,
                'time': time_str,
                'location': location,
                'link': event_url,
                'description': '',
                'source': 'Luma',
                'city': city_code
            })

        except Exception as e:
            print(f"Error parsing card: {e}")
            continue

    print(f"Extracted {len(events)} events")

    # Enrich from event pages when missing description/location
    for event in events:
        if not event.get('description') or event.get('location') == "Location TBA":
            details = await fetch_luma_details(event['link'])
            if details.get('description') and not event.get('description'):
                event['description'] = details['description']
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
    events = await scrape_luma("la")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['date']} {e['time']}")


if __name__ == '__main__':
    asyncio.run(main())

