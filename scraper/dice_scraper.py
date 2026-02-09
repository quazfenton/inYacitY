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


def _parse_dice_date_time(text: str) -> tuple:
    if not text:
        return ("", "")
    text = text.replace('•', ' ').strip()
    time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text, re.I)
    time_value = time_match.group(1).upper() if time_match else "TBA"
    month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', text, re.I)
    day_match = re.search(r'\b(\d{1,2})\b', text)
    if month_match and day_match:
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        month = month_map.get(month_match.group(1).lower(), datetime.now().month)
        day = int(day_match.group(1))
        year = datetime.now().year
        dt = datetime(year, month, day)
        if dt < datetime.now():
            dt = datetime(year + 1, month, day)
        return (dt.strftime("%Y-%m-%d"), time_value)
    return ("", time_value)


async def _fetch_dice_details(url: str) -> dict:
    details = {}
    try:
        html = await fetch_page(url, use_firecrawl_fallback=True)
        if not html:
            return details
        soup = BeautifulSoup(html, 'html.parser')
        title_elem = soup.find('h1')
        if title_elem:
            details['title'] = title_elem.get_text(" ", strip=True)
        date_elem = soup.find(class_=re.compile(r'EventDetailsTitle__Date', re.I))
        if date_elem:
            date_text = date_elem.get_text(" ", strip=True)
            date, time = _parse_dice_date_time(date_text)
            if date:
                details['date'] = date
            if time:
                details['time'] = time
        desc_container = soup.find(class_=re.compile(r'EventDetailsLayout__Content', re.I))
        if desc_container:
            desc_text = desc_container.get_text(" ", strip=True)
            if desc_text:
                details['description'] = desc_text[:800]
        venue_elem = soup.find(class_=re.compile(r'EventDetailsTitle__Venues', re.I))
        if venue_elem:
            details['location'] = venue_elem.get_text(" ", strip=True)
    except Exception:
        return details
    return details

async def scrape_dice(city: str = None, max_price: int = None) -> list:
    """Scrape Dice.fm events"""
    config = get_config()
    fetch_details = config.get_scraper_config('DICE_FM').get('fetch_details', True)
    
    if not city:
        city = config.get_location()
    
    # Get Dice.fm config
    dice_config = config.get_scraper_config('DICE_FM')
    city_map = dice_config.get('city_map', {})
    
    if max_price is None:
        max_price = dice_config.get('max_price', 0)
    
    output_file = "dice_events.json"
    
    # Build URL
    city_id = city_map.get(city, 'losangeles-5982e13c613de866017c3e3a')
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
            date_text = date_elem.get_text(strip=True) if date_elem else "TBA"
            event_date, event_time = _parse_dice_date_time(date_text)
            
            # Get venue
            venue_elem = card.find(class_=re.compile(r'Venue', re.I))
            venue = venue_elem.get_text(strip=True) if venue_elem else "Location TBA"
            
            events.append({
                'title': title,
                'date': event_date or "TBA",
                'time': event_time or "TBA",
                'location': venue,
                'link': href,
                'description': '',
                'source': 'Dice.fm'
            })
            
        except Exception as e:
            print(f"Error parsing card: {e}")
            continue
    
    print(f"Extracted {len(events)} events")
    
    # Fetch detail pages for missing fields
    for event in events:
        if fetch_details and (not event.get('date') or event.get('date') == "TBA" or not event.get('time') or event.get('time') == "TBA" or not event.get('description')):
            details = await _fetch_dice_details(event.get('link', ''))
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
    events = await scrape_dice("ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['date']}")


if __name__ == '__main__':
    asyncio.run(main())
