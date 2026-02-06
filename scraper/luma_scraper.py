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


async def scrape_luma(city: str = None) -> list:
    """Scrape Luma events for a city"""
    config = get_config()
    
    if not city:
        # Get location code and map to Luma format
        location = config.get_location()
        luma_map = config.get_city_map('LUMA')
        city = luma_map.get(location, 'la')
    
    output_file = "luma_events.json"
    
    # Convert city code
    if '--' in city:
        city = LUMA_CITIES.get(city, 'la')
    
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
            time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)', card_text)
            time_str = time_match.group(1) if time_match else "TBA"
            
            # Get location
            location = "Location TBA"
            # Look for text with venue-like patterns
            for elem in card.find_all(['div', 'span']):
                text = elem.get_text(strip=True)
                if len(text) > 3 and len(text) < 100 and not any(x in text.lower() for x in ['am', 'pm', 'min', 'hour']):
                    if not elem.find('h3') and not elem.find('a'):
                        location = text
                        break
            
            events.append({
                'title': title,
                'date': date_str,
                'time': time_str,
                'location': location,
                'link': event_url,
                'description': '',
                'source': 'Luma'
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
    events = await scrape_luma("la")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['date']} {e['time']}")


if __name__ == '__main__':
    asyncio.run(main())
