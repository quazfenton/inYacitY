#!/usr/bin/env python3
"""
Dice.fm event scraper for electronic music events
Supports configurable price filtering
"""

import asyncio
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from simple_browser import create_browser, close_browser


# Mapping of city codes to Dice.fm URLs
DICE_FM_CITY_MAP = {
    "dc--washington": "https://dice.fm/browse/washingtondc-5e3c290f136e51081e406ed6",
    "fl--miami": "https://dice.fm/browse/miami-5e3bf1b0fe75488ec46cdf9f",
    "ga--atlanta": "https://dice.fm/browse/atlanta-5d8a48ddb2b23e9f85bd478d",
    "il--chicago": "https://dice.fm/browse/chicago-5b238ca66e4bcd93783835b0",
    "on--toronto": "https://dice.fm/browse/toronto-5dfb2d3d7d9fd902f7ecdd5d",
    "ny--new-york": "https://dice.fm/browse/new_york-5bbf4db0f06331478e9b2c59",
    "pa--philadelphia": "https://dice.fm/browse/philadelphia-60f5b88857fe332ef6268244",
    "tx--austin": "https://dice.fm/browse/austin-5e3c24db136e51081e406ed3",
    "ca--san-francisco": "https://dice.fm/browse/sanfrancisco-60dee10ce5e339918757f0db",
    "ca--los-angeles": "https://dice.fm/browse/losangeles-5982e13c613de866017c3e3a",
    "ca--san-diego": "https://dice.fm/browse/san%20diego-5e3c28af136e51081e406ed5",
    "wa--seattle": "https://dice.fm/browse/seattle-5e3c245c136e51081e406ed1",
}


def build_dice_fm_url(base_url: str, max_price: Optional[int] = None) -> str:
    """
    Build Dice.fm URL with price filter
    
    Args:
        base_url: Base Dice.fm browse URL
        max_price: Maximum price in cents (None for no filter)
                   0 or less = free events only
                   1000+ = all events
                   other = events under that price
    
    Returns:
        Full URL with price filter
    """
    if max_price is None or max_price == 0:
        # Default: free events only
        return f"{base_url}?priceTo=1"
    elif max_price >= 1000:
        # No price filtering - show all events
        return base_url
    else:
        # Events under max_price
        return f"{base_url}?priceTo={max_price}"


async def fetch_dice_events_from_page(page, url: str) -> List[Dict]:
    """
    Scrape events from Dice.fm listing page using GraphQL API data in HTML
    """
    events = []
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        if hasattr(page, 'wait_for_timeout'):
            await page.wait_for_timeout(2000)
        else:
            await asyncio.sleep(2.0)
        
        # Get page content - handle both Playwright and pydoll
        if hasattr(page, 'content'):
            content = await page.content()
        else:
            result = await page.execute_script("return document.documentElement.outerHTML")
            if isinstance(result, dict) and 'result' in result:
                content = result['result']
            elif isinstance(result, dict) and 'value' in result:
                content = result['value']
            elif isinstance(result, str):
                content = result
            else:
                content = str(result) if result is not None else ""
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Dice.fm includes event data in the HTML (often from GraphQL responses)
        # Look for event cards with structured data
        event_cards = soup.find_all('a', class_=re.compile(r'EventCardLink'))
        
        print(f"Found {len(event_cards)} event cards on page")
        
        for card in event_cards:
            try:
                # Extract event link
                event_link = card.get('href', '')
                if not event_link:
                    continue
                
                if not event_link.startswith('http'):
                    event_link = f"https://dice.fm{event_link}"
                
                # Extract title from img alt text or div content
                img = card.find('img')
                title = img.get('alt', '') if img else ""
                
                if not title:
                    # Try to find title in structured divs
                    title_div = card.find('div', class_=re.compile(r'Title'))
                    if title_div:
                        title = title_div.get_text(strip=True)
                
                # Extract date
                date_div = card.find('div', class_=re.compile(r'DateText'))
                date_str = date_div.get_text(strip=True) if date_div else "TBA"
                
                # Extract venue/location
                venue_div = card.find('div', class_=re.compile(r'Venue'))
                venue = venue_div.get_text(strip=True) if venue_div else "Location TBA"
                
                if title and event_link:
                    event_info = {
                        'title': title,
                        'date': date_str,
                        'location': venue,
                        'link': event_link,
                        'source': 'Dice.fm'
                    }
                    events.append(event_info)
                    
            except Exception as e:
                print(f"Error extracting event: {e}")
                continue
        
        return events
        
    except Exception as e:
        print(f"Error navigating to {url}: {e}")
        return []


async def scrape_dice_fm_detail_page(page, event_url: str) -> Dict:
    """
    Scrape additional details from individual Dice.fm event page
    """
    details = {
        'description': 'Description not available',
        'price': 'TBA',
        'date_time': None,
        'coordinates': None
    }
    
    try:
        await page.goto(event_url, wait_until="domcontentloaded", timeout=15000)
        if hasattr(page, 'wait_for_timeout'):
            await page.wait_for_timeout(1500)
        else:
            await asyncio.sleep(1.5)
        
        # Get page content - handle both Playwright and pydoll
        if hasattr(page, 'content'):
            content = await page.content()
        else:
            result = await page.execute_script("return document.documentElement.outerHTML")
            if isinstance(result, dict) and 'result' in result:
                content = result['result']
            elif isinstance(result, dict) and 'value' in result:
                content = result['value']
            elif isinstance(result, str):
                content = result
            else:
                content = str(result) if result is not None else ""
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract description from about section
        about_section = soup.find('div', class_=re.compile(r'about', re.I))
        if about_section:
            description_elem = about_section.find('p') or about_section.find('div', recursive=True)
            if description_elem:
                details['description'] = description_elem.get_text(strip=True)[:500]
        
        # Extract price
        price_section = soup.find('div', class_=re.compile(r'price', re.I))
        if price_section:
            price_text = price_section.get_text(strip=True)
            details['price'] = price_text
        
        # Try to extract structured data from JSON-LD if available
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'Event':
                    details['date_time'] = data.get('startDate')
                    location_data = data.get('location', {})
                    if location_data:
                        details['coordinates'] = {
                            'lat': location_data.get('geo', {}).get('latitude'),
                            'lng': location_data.get('geo', {}).get('longitude')
                        }
            except:
                continue
        
        return details
        
    except Exception as e:
        print(f"Error scraping event detail page {event_url}: {e}")
        return details


async def scrape_dice_fm(
    city: str,
    max_price: Optional[int] = None,
    output_file: str = "dice_events.json"
) -> List[Dict]:
    """
    Main entry point for Dice.fm scraping
    
    Args:
        city: City code (e.g., 'ca--los-angeles')
        max_price: Maximum price in cents (None/0 = free only, 1000+ = all)
        output_file: Output JSON file path
    
    Returns:
        List of new events scraped
    """
    print(f"Scraping Dice.fm for {city} (max_price: {max_price})...")
    
    if city not in DICE_FM_CITY_MAP:
        print(f"City {city} not supported on Dice.fm")
        return []
    
    base_url = DICE_FM_CITY_MAP[city]
    url = build_dice_fm_url(base_url, max_price)
    
    # Load existing events to avoid duplicates
    existing_links = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                existing_links = {e.get("link") for e in data.get("events", [])}
            print(f"Loaded {len(existing_links)} existing events")
        except:
            pass
    
    all_events = []
    new_events = []
    
    browser = None
    browser_type = None
    
    try:
        browser, page = await create_browser(headless=True)
        
        print(f"Using {browser_type} browser")
        
        # Scrape listing page
        print(f"Scraping: {url}")
        events = await fetch_dice_events_from_page(page, url)
        print(f"Found {len(events)} events on listing page")
        
        # Filter duplicates and fetch details for new events
        for event in events:
            if event['link'] not in existing_links:
                # Optionally fetch detail page info
                # detail_info = await scrape_dice_fm_detail_page(page, event['link'])
                # event.update(detail_info)
                
                new_events.append(event)
                existing_links.add(event['link'])
                print(f"  ✓ {event['title'][:50]}")
        
        all_events.extend(events)
        
    except Exception as e:
        print(f"Error during Dice.fm scraping: {e}")
    
    finally:
        if browser:
            await close_browser(browser)
    
    # Save all events
    with open(output_file, 'w') as f:
        json.dump({
            "events": all_events,
            "count": len(all_events),
            "new": len(new_events)
        }, f, indent=2, default=str)
    
    print(f"Saved {len(all_events)} total events ({len(new_events)} new) to {output_file}")
    
    return new_events


async def main():
    """Test scraper"""
    import json
    
    # Load config
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except:
            pass
    
    city = config.get('LOCATION', 'ca--los-angeles')
    max_price = config.get('SOURCES', {}).get('DICE_FM', {}).get('max_price', 0)
    
    await scrape_dice_fm(city, max_price)


if __name__ == "__main__":
    asyncio.run(main())
