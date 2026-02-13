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


async def fetch_ra_co_events_from_page(page, url: str) -> List[Dict]:
    """
    Scrape events from RA.co listing page with retries and robust waiting
    """
    events = []
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}: Navigating to {url}")
            # Use networkidle for more stability if domcontentloaded is flaky
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check for blocking
            content = await page.content()
            if "blocked" in content.lower() or "security check" in content.lower() or "verify you are human" in content.lower():
                print(f"  ⚠️ Blocked on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue
                else:
                    return []

            soup = BeautifulSoup(content, 'html.parser')
            
            # Find event titles and links
            event_titles = soup.find_all('h3', attrs={"data-pw-test-id": "event-title"})
            
            if not event_titles:
                # Fallback selector
                event_titles = soup.select('h3[class*="EventTitle"]')
            
            print(f"Found {len(event_titles)} event titles on page")
            
            for title_elem in event_titles:
                try:
                    # Extract title and link from the link inside h3
                    link_elem = title_elem.find('a')
                    
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
                            'source': 'RA.co'
                        }
                        events.append(event_info)
                        
                except Exception as e:
                    print(f"Error extracting event title: {e}")
                    continue
            
            if events:
                return events
            
            # If no events found, maybe we need to scroll?
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await page.wait_for_timeout(2000)
            
        except Exception as e:
            print(f"Error navigating to {url} (Attempt {attempt + 1}): {e}")
            if "ERR_NAME_NOT_RESOLVED" in str(e):
                print("  DNS Resolution failed. Retrying with delay...")
            await asyncio.sleep(5)
            
    return events


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
        await page.wait_for_timeout(1500)
        
        content = await page.content()
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
    
    from consent_handler import (
        create_undetected_browser,
        close_undetected_browser,
        REAL_BROWSER_PROFILES,
        handle_consent_and_blockages
    )
    
    browser = None
    browser_type = None
    
    # Define profiles to try
    profiles_to_try = [
        'iphone_safari_17',
        'android_chrome_120',
        'windows_chrome_131',
        'macos_chrome_131'
    ]
    
    for profile_name in profiles_to_try:
        try:
            print(f"Attempting RA.co scrape with profile: {profile_name}")
            browser, page, browser_type = await create_undetected_browser(
                use_pydoll=True,
                use_patchright=True,
                headless=True,
                profile_name=profile_name
            )
            
            print(f"Using {browser_type} browser")
            
            # Scrape listing page
            print(f"Scraping: {url}")
            events = await fetch_ra_co_events_from_page(page, url)
            
            # Check if we were blocked (too few events or specific content)
            if len(events) < 5:
                content = await page.content()
                if "blocked" in content.lower() or "security check" in content.lower():
                    print(f"⚠️  Blocked with profile {profile_name}. Retrying with next profile...")
                    await close_undetected_browser(browser, browser_type)
                    browser = None
                    continue
            
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
                    
                    print(f"  ✓ {event['title'][:50]}")
            
            all_events.extend(events)
            
            # If we got here and have events, we succeeded
            if len(all_events) > 0:
                break
                
        except Exception as e:
            print(f"Error during RA.co scraping with profile {profile_name}: {e}")
            if browser:
                await close_undetected_browser(browser, browser_type)
                browser = None
            continue
    
    # Cleanup browser if it's still open
    if browser:
        await close_undetected_browser(browser, browser_type)
    
    # Load existing events to preserve them
    existing_events = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_data = json.load(f)
                existing_events = existing_data.get("events", [])
        except:
            pass  # If there's an error reading the file, start fresh

    # Combine existing events with new events, avoiding duplicates by link
    all_links = set()
    combined_events = []

    # Add existing events first
    for event in existing_events:
        link = event.get('link', '')
        if link and link not in all_links:
            combined_events.append(event)
            all_links.add(link)

    # Add new events that aren't already in the existing set
    for event in all_events:
        link = event.get('link', '')
        if link and link not in all_links:
            combined_events.append(event)
            all_links.add(link)

    # Save combined events
    with open(output_file, 'w') as f:
        json.dump({
            "events": combined_events,
            "count": len(combined_events),
            "new": len(new_events)
        }, f, indent=2, default=str)

    print(f"Saved {len(combined_events)} total events ({len(new_events)} new) to {output_file}")
    
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