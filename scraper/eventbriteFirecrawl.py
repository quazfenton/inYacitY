#!/usr/bin/env python3
"""
Fixed Eventbrite scraper using Firecrawl API
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
import aiohttp
from bs4 import BeautifulSoup


FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")


async def fetch_with_firecrawl(url: str) -> Optional[str]:
    """Fetch page content using Firecrawl API"""
    if not FIRECRAWL_API_KEY:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "url": url,
                "formats": ["html"]
            }
            
            async with session.post(
                "https://api.firecrawl.dev/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success") and data.get("data"):
                        return data["data"].get("html", "")
                else:
                    print(f"Firecrawl error: {resp.status}")
    except Exception as e:
        print(f"Firecrawl error: {e}")
    return None


def parse_date(date_str: str) -> tuple:
    """Parse Eventbrite date string into date and time"""
    if not date_str or date_str == 'TBA':
        return 'TBA', 'TBA'
    
    # Pattern: "Thu, Feb 19, 5:00 PM"
    match = re.match(r'([A-Za-z]{3}),?\s+([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{1,2}):(\d{2})\s*(AM|PM)', date_str)
    if match:
        month_map = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                     'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
        day = match.group(3).zfill(2)
        month = month_map.get(match.group(2), '01')
        year = datetime.now().year
        
        date_formatted = f"{year}-{month}-{day}"
        time_formatted = f"{match.group(4)}:{match.group(5)} {match.group(6)}"
        return date_formatted, time_formatted
    
    return date_str, 'TBA'


def extract_events_from_html(html: str) -> List[Dict]:
    """Extract events from Eventbrite HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # Find all event cards
    event_cards = soup.find_all(attrs={'data-testid': 'search-event'})
    print(f"Found {len(event_cards)} event cards")
    
    for card in event_cards:
        try:
            # Get link and title from event-card-link
            link_elem = card.find('a', class_='event-card-link')
            if not link_elem:
                continue
            
            # Title is in aria-label (format: "View Event Title")
            title = link_elem.get('aria-label', '').replace('View ', '')
            if not title:
                continue
            
            href = link_elem.get('href', '')
            if not href:
                continue
            
            # Clean up URL
            if href.startswith('/'):
                href = f"https://www.eventbrite.com{href}"
            
            # Get location from data attribute
            location = link_elem.get('data-event-location', 'Location TBA')
            
            # Get date from text content
            date_match = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{1,2}):(\d{2})\s*(AM|PM)', card.get_text())
            if date_match:
                date_str = date_match.group(0)
                date_formatted, time_formatted = parse_date(date_str)
            else:
                date_formatted, time_formatted = 'TBA', 'TBA'
            
            events.append({
                'title': title,
                'link': href,
                'date': date_formatted,
                'time': time_formatted,
                'location': location,
                'description': 'Description not available',
                'source': 'Eventbrite',
                'price': 0
            })
            
        except Exception as e:
            continue
    
    return events


async def scrape_eventbrite(city: str, output_file: str = "eventbrite_events.json", pages: int = 2):
    """Scrape Eventbrite events"""
    base_url = f"https://www.eventbrite.com/d/{city}/free--events/"
    all_events = []
    existing_links = set()
    
    # Load existing events
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                for event in data.get('events', []):
                    existing_links.add(event['link'])
                    all_events.append(event)
            print(f"Loaded {len(all_events)} existing events")
        except:
            pass
    
    for page_num in range(1, pages + 1):
        url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
        print(f"\nScraping page {page_num}: {url}")
        
        html = await fetch_with_firecrawl(url)
        if not html:
            print("Failed to fetch page")
            continue

                events = extract_events_from_html(html)
                print(f"Extracted {len(events)} events")

                # Add new events
                new_count = 0
                for event in events:
                    if event['link'] not in existing_links:
                        all_events.append(event)
                        existing_links.add(event['link'])
                        new_count += 1

                print(f"Added {new_count} new events")

            # Save
            with open(output_file, 'w') as f:
                json.dump({
                    'events': all_events,
                    'total': len(all_events),
                    'new': new_count
                }, f, indent=2, default=str)

            print(f"\n✓ Saved {len(all_events)} total events to {output_file}")
            return all_events

async def main():
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except:
            pass
    
    location = config.get('LOCATION', 'ca--los-angeles')
    await scrape_eventbrite(location)


if __name__ == '__main__':
    asyncio.run(main())
