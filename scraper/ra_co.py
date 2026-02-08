#!/usr/bin/env python3
"""
RA.co event scraper for electronic music events
Supports city-based filtering with standardized URL format
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
from browser import fetch_page


# Mapping of city codes to RA.co URL segments
# Format: city_code -> (country_slug, city_slug)
RA_CO_CITY_MAP = {
    "dc--washington": ("us", "washingtondc"),
    "fl--miami": ("us", "miami"),
    "ga--atlanta": ("us", "atlanta"),
    "il--chicago": ("us", "chicago"),
    "ny--new-york": ("us", "newyorkcity"),
    "pa--philadelphia": ("us", "philadelphia"),
    "tx--austin": ("us", "austin"),
    "ca--san-francisco": ("us", "sanfrancisco"),
    "ca--los-angeles": ("us", "losangeles"),
    "ca--san-diego": ("us", "sandiego"),
    "wa--seattle": ("us", "seattle"),
    "co--denver": ("us", "denver"),
    "ma--boston": ("us", "boston"),
    "tx--houston": ("us", "houston"),
    "az--phoenix": ("us", "phoenix"),
    "tx--dallas": ("us", "dallas"),
    "wa--seattle": ("us", "seattle"),
    "nv--las-vegas": ("us", "lasvegas"),
    "ut--salt-lake-city": ("us", "saltlakecity"),
    "on--toronto": ("ca", "toronto"),
}


def build_ra_co_url(city_code: str) -> str:
    """
    Build RA.co URL for a city
    
    Args:
        city_code: City code (e.g., 'ca--los-angeles')
    
    Returns:
        Full RA.co events URL
    """
    if city_code not in RA_CO_CITY_MAP:
        return None
    
    country, city = RA_CO_CITY_MAP[city_code]
    return f"https://ra.co/events/{country}/{city}"


def _looks_blocked(html: str) -> bool:
    if not html:
        return True
    text = html.lower()
    indicators = [
        'access denied',
        'verify you are human',
        'captcha',
        'datadome',
        'incident id',
        'blocked',
        'challenge',
    ]
    return any(indicator in text for indicator in indicators)


def _parse_listing_html(html: str, city: str) -> List[Dict]:
    events: List[Dict] = []
    if not html:
        return events

    soup = BeautifulSoup(html, 'html.parser')
    event_titles = soup.find_all('h3', attrs={"data-pw-test-id": "event-title"})

    for title_elem in event_titles:
        try:
            link_elem = title_elem.find('a', attrs={"data-pw-test-id": "event-title-link"})
            if not link_elem:
                continue
            event_link = link_elem.get('href', '')
            title = link_elem.get_text(strip=True)
            if not event_link.startswith('http'):
                event_link = f"https://ra.co{event_link}"
            if title and event_link:
                event_info = {
                    'title': title,
                    'link': event_link,
                    'date': 'TBA',
                    'time': 'TBA',
                    'location': 'TBA',
                    'price': 'TBA',
                    'source': 'RA.co',
                    'city': city
                }
                parent = title_elem.find_parent()
                if parent:
                    date_elem = parent.find(string=re.compile(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s*\d+\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', re.I))
                    if date_elem:
                        event_info['date'] = str(date_elem).strip()
                    venue_link = parent.find('span', attrs={"data-pw-test-id": "event-venue-link"})
                    if venue_link:
                        event_info['location'] = venue_link.get_text(strip=True)
                events.append(event_info)
        except Exception:
            continue

    return events


async def fetch_ra_co_events_from_page(page, url: str, city: str) -> List[Dict]:
    """
    Scrape events from RA.co listing page
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
        
        events = _parse_listing_html(content, city)
        print(f"Found {len(events)} event titles on page")
        return events
        
    except Exception as e:
        print(f"Error navigating to {url}: {e}")
        return []


async def scrape_ra_co_detail_page(page, event_url: str) -> Dict:
    """
    Scrape detailed information from individual RA.co event page
    """
    details = {
        'date': 'TBA',
        'time': 'TBA',
        'location': 'TBA',
        'description': 'Description not available',
        'price': 'TBA',
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
        
        # Extract title from h1
        h1_elem = soup.find('h1')
        if h1_elem:
            title_span = h1_elem.find('span')
            if title_span:
                title = title_span.get_text(strip=True)
        
        # Extract event details from event-detail-bar
        detail_bar = soup.find('div', attrs={"data-tracking-id": "event-detail-bar"})
        
        if detail_bar:
            # Find the list of details (Location, Date/Time, etc.)
            detail_list = detail_bar.find('ul')
            
            if detail_list:
                columns = detail_list.find_all('li', class_=re.compile(r'Column'))
                
                for column in columns:
                    column_text = column.get_text(strip=True)
                    
                    # Try to identify what type of detail this is
                    # Look for date patterns (e.g., "Sat, 7 Feb 2026")
                    if re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+\d+\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', column_text):
                        details['date'] = column_text
                    
                    # Look for time patterns
                    elif re.search(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)', column_text):
                        details['time'] = column_text
                    
                    # Check if it's a location (usually has address-like patterns)
                    elif re.search(r'(Street|Ave|Road|St|Place|Blvd|Lane|Drive|Way|Dr)', column_text):
                        details['location'] = column_text
        
        # Extract description from event-description section
        desc_section = soup.find('section', id="event-description")
        
        if desc_section:
            # Find description content
            desc_divs = desc_section.find_all('div', class_=re.compile(r'Column'))
            
            for div in desc_divs:
                div_text = div.get_text(strip=True)
                # Skip price/cost information, look for actual description
                if len(div_text) > 100 and not re.search(r'(Price|Cost|Free|€|\$|£)', div_text):
                    details['description'] = div_text[:500]
                    break
            
            # Extract price/cost
            cost_span = desc_section.find('span', class_=re.compile(r'price|cost', re.I))
            if cost_span:
                details['price'] = cost_span.get_text(strip=True)
        
        # Try to extract structured data from JSON-LD
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'Event':
                    if not details['date'] or details['date'] == 'TBA':
                        details['date'] = data.get('startDate', '')
                    
                    location_data = data.get('location', {})
                    if location_data and location_data.get('name'):
                        details['location'] = location_data.get('name')
                    
                    if location_data.get('geo'):
                        details['coordinates'] = {
                            'lat': location_data['geo'].get('latitude'),
                            'lng': location_data['geo'].get('longitude')
                        }
            except:
                continue
        
        return details
        
    except Exception as e:
        print(f"Error scraping event detail page {event_url}: {e}")
        return details


async def scrape_ra_co(
    city: str,
    output_file: str = "ra_co_events.json",
    fetch_details: bool = True
) -> List[Dict]:
    """
    Main entry point for RA.co scraping
    
    Args:
        city: City code (e.g., 'ca--los-angeles')
        output_file: Output JSON file path
        fetch_details: Whether to fetch detail pages for each event
    
    Returns:
        List of new events scraped
    """
    print(f"Scraping RA.co for {city}...")
    
    url = build_ra_co_url(city)
    if not url:
        print(f"City {city} not supported on RA.co")
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
    
    browser = None
    browser_type = None
    
    try:
        browser, page = await create_browser(headless=True)
        
        print(f"Using simple browser")
        
        # Scrape listing page
        print(f"Scraping: {url}")
        events = await fetch_ra_co_events_from_page(page, url, city)
        if not events:
            content = await page.content()
            if _looks_blocked(content):
                print("Listing appears blocked. Trying Firecrawl/Playwright fallback.")
                html = await fetch_page(url, use_firecrawl_fallback=True)
                events = _parse_listing_html(html, city)
        print(f"Found {len(events)} events on listing page")
        
        # Filter duplicates
        for event in events:
            if event['link'] not in existing_links:
                new_events.append(event)
                existing_links.add(event['link'])
                
                # Optionally fetch detail page information
                if fetch_details:
                    print(f"  Fetching details for: {event['title'][:50]}")
                    detail_info = await scrape_ra_co_detail_page(page, event['link'])
                    event.update(detail_info)
                event.setdefault('city', city)
                
                print(f"  ✓ {event['title'][:50]}")
        
        all_events.extend(events)
        
    except Exception as e:
        print(f"Error during RA.co scraping: {e}")
    
    finally:
        if browser:
            await close_browser(browser)

    # Fallback: mobile context if still empty
    if not events:
        print("Retrying RA.co with mobile context...")
        browser = None
        try:
            p = await async_playwright().start()
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                viewport={'width': 375, 'height': 812},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            html = await page.content()
            events = _parse_listing_html(html, city)
            await browser.close()
            await p.stop()
        except Exception as e:
            print(f"Mobile fallback failed: {e}")
            if browser:
                await browser.close()
    
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
    
    await scrape_ra_co(city, fetch_details=True)


if __name__ == "__main__":
    asyncio.run(main())
