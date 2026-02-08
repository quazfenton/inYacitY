#!/usr/bin/env python3
"""
Posh.vip Event Scraper

Scrapes club/nightlife events from posh.vip
Features:
- Club party events
- VIP/general admission tiers
- Open bar detection
- Manual scraping (on-demand only)
- Tagged as "club" by default
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


# Mapping of city codes to posh.vip URL parameters
POSH_VIP_CITY_MAP = {
    "ca--los-angeles": "los-angeles",
    "ca--san-diego": "san-diego",
    "ca--san-francisco": "san-francisco",
    "dc--washington": "washington-dc",
    "fl--miami": "miami",
    "ga--atlanta": "atlanta",
    "il--chicago": "chicago",
    "ny--new-york": "new-york",
    "pa--philadelphia": "philadelphia",
    "tx--austin": "austin",
    "tx--dallas": "dallas",
    "tx--houston": "houston",
    "wa--seattle": "seattle",
    "co--denver": "denver",
    "nv--las-vegas": "las-vegas",
    "ma--boston": "boston",
}


def build_posh_vip_url(city_code: str) -> Optional[str]:
    """
    Build posh.vip URL for a city
    
    Args:
        city_code: City code (e.g., 'ca--los-angeles')
    
    Returns:
        Full posh.vip URL or None
    """
    if city_code not in POSH_VIP_CITY_MAP:
        return None
    
    city_slug = POSH_VIP_CITY_MAP[city_code]
    return f"https://posh.vip/events/{city_slug}"


async def fetch_posh_vip_events_from_page(page, url: str) -> List[Dict]:
    """
    Scrape events from posh.vip listing page
    
    Detects:
    - Event title
    - Date and time
    - Venue
    - Event link
    - Price tiers (VIP, General)
    - Open bar indicators
    """
    events = []
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find event cards
        # posh.vip typically uses event-card or similar containers
        event_cards = soup.find_all('div', class_=re.compile(r'event|card', re.I))
        
        print(f"Found {len(event_cards)} potential event cards on page")
        
        for card in event_cards:
            try:
                # Extract event link
                link_elem = card.find('a', href=True)
                if not link_elem:
                    continue
                
                event_link = link_elem.get('href', '')
                if not event_link.startswith('http'):
                    event_link = f"https://posh.vip{event_link}"
                
                # Extract title
                title_elem = card.find(['h2', 'h3', 'h4'])
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                # Extract date/time
                date_elem = card.find(['span', 'div'], class_=re.compile(r'date|time', re.I))
                date_str = date_elem.get_text(strip=True) if date_elem else "TBA"
                
                # Extract venue
                venue_elem = card.find(['span', 'div'], class_=re.compile(r'venue|location', re.I))
                venue = venue_elem.get_text(strip=True) if venue_elem else "Location TBA"
                
                # Detect price information
                price_text = card.get_text()
                
                # Detect open bar
                has_open_bar = bool(re.search(r'open\s+bar|complimentary\s+drinks', price_text, re.I))
                
                # Try to extract price
                price_match = re.search(r'\$(\d+)', price_text)
                price = int(price_match.group(1)) * 100 if price_match else 0  # Convert to cents
                
                event_info = {
                    'title': title,
                    'date': date_str,
                    'location': venue,
                    'link': event_link,
                    'source': 'Posh.vip',
                    'city': city,
                    'category': 'club',  # Always tagged as club event
                    'price': price,
                    'has_open_bar': has_open_bar,
                    'description': 'Club/nightlife event'
                }
                
                events.append(event_info)
                print(f"  ✓ {title[:50]}")
                
            except Exception as e:
                print(f"Error extracting event: {e}")
                continue
        
        return events
        
    except Exception as e:
        print(f"Error navigating to {url}: {e}")
        return []


async def scrape_posh_vip_detail_page(page, event_url: str) -> Dict:
    """
    Scrape additional details from individual posh.vip event page
    """
    details = {
        'description': 'Club/nightlife event',
        'full_details': None,
        'dress_code': None,
        'age_restriction': None,
    }
    
    try:
        await page.goto(event_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract description
        desc_elem = soup.find('div', class_=re.compile(r'description|details', re.I))
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)[:500]
        
        # Extract dress code
        dress_code_text = soup.get_text()
        dress_match = re.search(r'dress\s+code[:\s]+([^\n]+)', dress_code_text, re.I)
        if dress_match:
            details['dress_code'] = dress_match.group(1).strip()
        
        # Extract age restriction
        age_match = re.search(r'(\d+)\+\s+only|must\s+be\s+(\d+)', dress_code_text, re.I)
        if age_match:
            details['age_restriction'] = age_match.group(1) or age_match.group(2)
        
        return details
        
    except Exception as e:
        print(f"Error scraping event detail page {event_url}: {e}")
        return details


async def scrape_posh_vip(
    city: str,
    output_file: str = "posh_vip_events.json",
    fetch_details: bool = False  # Default: don't fetch details (on-demand only)
) -> List[Dict]:
    """
    Main entry point for posh.vip scraping
    
    NOTE: posh.vip is manually triggered (on-demand only)
    
    Args:
        city: City code (e.g., 'ca--los-angeles')
        output_file: Output JSON file path
        fetch_details: Whether to fetch detail pages (default: False)
    
    Returns:
        List of new events scraped
    """
    print(f"Scraping Posh.vip for {city} (on-demand)...")
    
    url = build_posh_vip_url(city)
    if not url:
        print(f"City {city} not supported on Posh.vip")
        return []
    
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
    
    from consent_handler import (
        create_undetected_browser,
        close_undetected_browser,
    )
    
    browser = None
    browser_type = None
    
    try:
        browser, page, browser_type = await create_undetected_browser(
            use_pydoll=True,
            use_patchright=True,
            headless=True
        )
        
        print(f"Using {browser_type} browser")
        
        # Scrape listing page
        print(f"Scraping: {url}")
        events = await fetch_posh_vip_events_from_page(page, url)
        print(f"Found {len(events)} events on listing page")
        
        # Filter duplicates
        for event in events:
            if event['link'] not in existing_links:
                new_events.append(event)
                existing_links.add(event['link'])
                
                # Optionally fetch detail page (not done by default)
                if fetch_details:
                    print(f"  Fetching details for: {event['title'][:50]}")
                    detail_info = await scrape_posh_vip_detail_page(page, event['link'])
                    event.update(detail_info)
                
                print(f"  ✓ {event['title'][:50]}")
        
        all_events.extend(events)
        
    except Exception as e:
        print(f"Error during Posh.vip scraping: {e}")
    
    finally:
        if browser:
            await close_undetected_browser(browser, browser_type)
    
    # Save all events
    with open(output_file, 'w') as f:
        json.dump({
            "events": all_events,
            "count": len(all_events),
            "new": len(new_events),
            "notes": "Posh.vip events - club/nightlife only - manually triggered"
        }, f, indent=2, default=str)
    
    print(f"Saved {len(all_events)} total events ({len(new_events)} new) to {output_file}")
    
    return new_events


async def main():
    """Test scraper - manual trigger only"""
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
    
    print("\n" + "="*70)
    print("POSH.VIP SCRAPER - MANUAL TRIGGER")
    print("="*70)
    print("This scraper is designed for on-demand triggering only.")
    print("It is NOT automatically scheduled in the main scraper.")
    print("="*70 + "\n")
    
    await scrape_posh_vip(city, fetch_details=False)


if __name__ == "__main__":
    asyncio.run(main())
