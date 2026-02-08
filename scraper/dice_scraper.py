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


async def scrape_dice(city: str = None, max_price: int = None) -> list:
    """Scrape Dice.fm events"""
    config = get_config()
    
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
