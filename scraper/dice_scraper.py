#!/usr/bin/env python3
"""
Dice.fm scraper - Playwright primary, Firecrawl fallback
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from browser import fetch_page
from config_loader import get_config


def parse_month_day(date_text: str) -> str:
    """Parse 'Tue, Feb 10' to YYYY-MM-DD."""
    if not date_text:
        return ""
    today = datetime.now()
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})', date_text)
    if not match:
        return ""
    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    month = month_map.get(match.group(1))
    day = int(match.group(2))
    year = today.year
    try:
        event_date = datetime(year, month, day)
        # Only bump to next year if the event date is actually in the past (before today's date)
        # Comparing date() parts ensures we only compare the date, not the time
        if event_date.date() < today.date():
            event_date = datetime(year + 1, month, day)
        return event_date.strftime("%Y-%m-%d")
    except ValueError:
        return ""


def extract_time(date_text: str) -> str:
    """Extract time like '9:00 PM' from text."""
    if not date_text:
        return ""
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*[AP]M)', date_text, re.I)
    return match.group(1).upper().replace(' ', '') if match else ""


def parse_datetime_from_text(text: str) -> tuple:
    if not text:
        return ("", "")
    date_val = parse_month_day(text)
    time_val = extract_time(text)
    return (date_val, time_val)


def clean_dice_description(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'\s+', ' ', text).strip()
    if ' About ' in cleaned:
        cleaned = cleaned.split(' About ', 1)[1].strip()
    cleaned = re.sub(r'^.*?No surprises later\.\s*', '', cleaned, flags=re.I).strip()
    # Cut off at "..." which indicates "Read more" truncation
    if '...' in cleaned:
        cleaned = cleaned.split('...')[0].strip()
        cleaned = cleaned + "..."
    return cleaned


async def fetch_dice_details(url: str) -> dict:
    """Fetch description/date/time/location from Dice event page."""
    html = await fetch_page(url, use_firecrawl_fallback=True)
    if not html:
        return {}
    soup = BeautifulSoup(html, 'html.parser')
    details = {}

    date_elem = soup.find(class_=re.compile(r'EventDetailsTitle__Date', re.I))
    if date_elem:
        date_text = date_elem.get_text(strip=True)
        details['date_text'] = date_text

    venue_elem = soup.find(class_=re.compile(r'EventDetailsTitle__Venues', re.I))
    if venue_elem:
        details['location'] = venue_elem.get_text(strip=True)

    desc_container = soup.find(class_=re.compile(r'EventDetailsLayout__Content', re.I))
    if desc_container:
        details['description'] = clean_dice_description(desc_container.get_text(" ", strip=True))[:500]

    return details


async def scrape_dice(city: str = None, max_price: int = None) -> list:
    """Scrape Dice.fm events"""
    config = get_config()

    city_code = None
    if not city:
        city = config.get_location()
        city_code = city
    else:
        city_code = city

    # Get Dice.fm config
    dice_config = config.get_scraper_config('DICE_FM')
    city_map = dice_config.get('city_map', {})

    # Check if city is supported
    if city_code not in city_map:
        print(f"⚠ Dice.fm: City '{city_code}' not supported. Skipping.")
        return []

    if max_price is None:
        max_price = dice_config.get('max_price', 0)

    output_file = os.path.join(os.path.dirname(__file__), "dice_events.json")

    # Build URL
    city_id = city_map.get(city)

    url = f"https://dice.fm/browse/{city_id}"
    if max_price == 0:
        url += "?priceTo=1"  # Free events
    elif max_price > 0:
        url += f"?priceTo={max_price}"

    print(f"\nScraping Dice.fm: {url}")

    # Fetch page
    html = await fetch_page(url, use_firecrawl_fallback=True)
    if not html:
        print("Failed to fetch Dice.fm page")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    events = []

    # Dice uses EventCardLink class
    event_cards = soup.find_all('a', class_=re.compile(r'EventCardLink', re.I))
    print(f"Found {len(event_cards)} event cards")

    for card in event_cards:
        try:
            # Get link
            href = card.get('href', '')
            if not href:
                continue

            if not href.startswith('http'):
                href = f"https://dice.fm{href}"

            # Get title from img alt
            img = card.find('img')
            title = img.get('alt', '') if img else ''

            if not title:
                # Try other selectors
                title_elem = card.find(['h3', 'h2', 'h1']) or card.find(class_=re.compile(r'title', re.I))
                if title_elem:
                    title = title_elem.get_text(strip=True)

            if not title:
                continue

            # Get date
            date_elem = card.find(class_=re.compile(r'DateText', re.I))
            date_text = date_elem.get_text(strip=True) if date_elem else ""
            event_date = parse_month_day(date_text)
            event_time = extract_time(date_text)

            # Get venue
            venue_elem = card.find(class_=re.compile(r'Venue', re.I))
            venue = venue_elem.get_text(strip=True) if venue_elem else "Location TBA"

            events.append({
                'title': title,
                'date': event_date,
                'time': event_time,
                'location': venue,
                'link': href,
                'description': '',
                'source': 'Dice.fm',
                'city': city_code
            })

        except Exception as e:
            print(f"Error parsing card: {e}")
            continue

    print(f"Extracted {len(events)} events")

    # Enrich with event pages when missing date/time/description/location
    for event in events:
        if not event.get('date') or not event.get('time') or not event.get('description') or event.get('location') == "Location TBA":
            details = await fetch_dice_details(event['link'])
            if details.get('date_text'):
                if not event.get('date'):
                    event['date'] = parse_month_day(details['date_text'])
                if not event.get('time'):
                    event['time'] = extract_time(details['date_text'])
            if details.get('location') and event.get('location') == "Location TBA":
                event['location'] = details['location']
            if details.get('description') and not event.get('description'):
                event['description'] = details['description']

        if (not event.get('date') or not event.get('time')) and event.get('description'):
            d_val, t_val = parse_datetime_from_text(event['description'])
            if d_val and not event.get('date'):
                event['date'] = d_val
            if t_val and not event.get('time'):
                event['time'] = t_val

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
    events = await scrape_dice("ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['date']}")


if __name__ == '__main__':
    asyncio.run(main())

