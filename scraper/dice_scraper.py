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


# City mapping
DICE_CITIES = {
    'ca--los-angeles': 'losangeles-5982e13c613de866017c3e3a',
    'ny--new-york': 'new_york-5bbf4db0f06331478e9b2c59',
    'fl--miami': 'miami-5e3bf1b0fe75488ec46cdf9f',
    'il--chicago': 'chicago-5b238ca66e4bcd93783835b0',
    'tx--austin': 'austin-5e3c24db136e51081e406ed3',
    'ca--san-francisco': 'sanfrancisco-60dee10ce5e339918757f0db',
}


async def scrape_dice(city: str = "ca--los-angeles", max_price: int = 0) -> list:
    """Scrape Dice.fm events"""
    output_file = "dice_events.json"
    
    # Build URL
    city_id = DICE_CITIES.get(city, 'losangeles-5982e13c613de866017c3e3a')
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
            
            # Get venue
            venue_elem = card.find(class_=re.compile(r'Venue', re.I))
            venue = venue_elem.get_text(strip=True) if venue_elem else "Location TBA"
            
            events.append({
                'title': title,
                'date': date_text,
                'time': '',
                'location': venue,
                'link': href,
                'description': '',
                'source': 'Dice.fm'
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
    events = await scrape_dice("ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['date']}")


if __name__ == '__main__':
    asyncio.run(main())
