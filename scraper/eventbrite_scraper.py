#!/usr/bin/env python3
"""
Eventbrite scraper - Playwright primary, Firecrawl fallback
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from browser import fetch_page
from config_loader import get_config


def _clean_date_text(date_str: str) -> str:
    return date_str.replace('•', ' ').replace('|', ' ').strip()


def parse_event_date(date_str: str) -> str:
    """Parse various date formats to YYYY-MM-DD"""
    today = datetime.now()
    date_str = _clean_date_text(date_str)
    
    # Handle relative dates
    if "today" in date_str.lower():
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in date_str.lower():
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Parse formats like "Thu, Feb 19, 5:00 PM"
    patterns = [
        r'([A-Za-z]+),?\s+([A-Za]+)\s+(\d{1,2}),?\s+(\d{1,2}:\d{2}\s*[AP]M)',
        r'([A-Za]+)\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                # Try to parse with current year if not provided
                if len(match.groups()) >= 2:
                    month_str = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    day_str = match.group(3) if len(match.groups()) > 2 else match.group(2)
                    
                    month_map = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
                        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                    }
                    
                    month = month_map.get(month_str.lower(), 1)
                    day = int(day_str)
                    year = today.year
                    
                    # If date is in past, assume next year
                    event_date = datetime(year, month, day)
                    if event_date < today:
                        event_date = datetime(year + 1, month, day)
                    
                    return event_date.strftime("%Y-%m-%d")
            except:
                pass
    
    # Fallback to month name detection
    month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_str, re.I)
    day_match = re.search(r'\b(\d{1,2})\b', date_str)
    if month_match and day_match:
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        month = month_map.get(month_match.group(1).lower(), today.month)
        day = int(day_match.group(1))
        event_date = datetime(today.year, month, day)
        if event_date < today:
            event_date = datetime(today.year + 1, month, day)
        return event_date.strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")


def extract_time(date_str: str) -> str:
    """Extract time from date string"""
    date_str = _clean_date_text(date_str)
    time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', date_str, re.I)
    if time_match:
        return time_match.group(1).upper().replace(' ', '')
    return "TBA"


def parse_events_from_html(html: str) -> list:
    """Parse events from Eventbrite HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # Find event cards - Eventbrite uses data-testid="search-event"
    event_cards = soup.find_all(attrs={'data-testid': 'search-event'})
    
    if not event_cards:
        # Try alternative selectors
        event_cards = soup.find_all('div', class_=re.compile(r'event-card|search-result', re.I))
    
    print(f"Found {len(event_cards)} event cards")
    
    for card in event_cards:
        try:
            # Get link
            link_elem = card.find('a', class_=re.compile(r'event-card-link', re.I))
            if not link_elem:
                link_elem = card.find('a', href=re.compile(r'/e/'))
            
            if not link_elem:
                continue
                
            href = link_elem.get('href', '')
            if not href:
                continue
            
            # Clean up URL
            if href.startswith('/'):
                href = f"https://www.eventbrite.com{href}"
            href = href.split('?')[0]  # Remove query params
            
            # Get title - try aria-label first, then text content
            title = link_elem.get('aria-label', '')
            if not title:
                title_elem = card.find(['h3', 'h2', 'h1']) or card.find(class_=re.compile(r'title', re.I))
                if title_elem:
                    title = title_elem.get_text(strip=True)

            if not title:
                continue
            if title.lower().startswith('view '):
                title = title[5:].strip()
            if title.lower().startswith('view'):
                title = title[4:].strip()
            
            # Get date/time
            date_text = ""
            date_elem = card.find(attrs={'data-testid': re.compile(r'date|time', re.I)})
            if date_elem:
                date_text = date_elem.get_text(strip=True)
            if not date_text:
                for p in card.find_all('p'):
                    text = p.get_text(" ", strip=True)
                    if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', text, re.I):
                        date_text = text
                        break
            
            if not date_text:
                # Try finding in any text
                date_match = re.search(r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2}[^\n]*)', card.get_text())
                if date_match:
                    date_text = date_match.group(1)
            
            # Parse date and time
            event_date = parse_event_date(date_text)
            event_time = extract_time(date_text)
            
            # Get location
            location = "Location TBA"
            location_elem = card.find(attrs={'data-testid': re.compile(r'location|venue', re.I)})
            if location_elem:
                location = location_elem.get_text(strip=True)
            else:
                for p in card.find_all('p'):
                    text = p.get_text(" ", strip=True)
                    if '·' in text and not re.search(r'\b(?:am|pm)\b', text, re.I):
                        location = text
                        break
                if location == "Location TBA":
                    loc_match = re.search(r'([A-Za-z\s]+,\s*[A-Z]{2})', card.get_text())
                    if loc_match:
                        location = loc_match.group(1)
            
            events.append({
                'title': title,
                'date': event_date,
                'time': event_time,
                'location': location,
                'link': href,
                'description': '',
                'source': 'Eventbrite'
            })
            
        except Exception as e:
            print(f"Error parsing card: {e}")
            continue
    
    return events


async def scrape_eventbrite(location: str = None, max_pages: int = None) -> list:
    """Scrape Eventbrite events for a location"""
    config = get_config()
    
    if not location:
        location = config.get_location()
    
    # Get Eventbrite config
    eb_config = config.get_scraper_config('EVENTBRITE')
    if max_pages is None:
        max_pages = eb_config.get('main_pages', 2)
    
    output_file = "eventbrite_events.json"
    
    # Load existing events
    existing_links = set()
    existing_events = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                existing_events = data.get('events', [])
                existing_links = {e.get('link', '') for e in existing_events}
            print(f"Loaded {len(existing_links)} existing events")
        except:
            pass
    
    all_events = list(existing_events)
    base_url = eb_config.get('base_url', 'https://www.eventbrite.com/d/{location}/free--events/').format(location=location)
    
    # Scrape multiple pages
    for page in range(1, max_pages + 1):
        url = base_url if page == 1 else f"{base_url}?page={page}"
        
        print(f"\nScraping page {page}: {url}")
        
        html = await fetch_page(url, use_firecrawl_fallback=True)
        if not html:
            print(f"Failed to fetch page {page}")
            continue
        
        events = parse_events_from_html(html)
        print(f"Extracted {len(events)} events from page {page}")
        
        # Filter duplicates
        for e in events:
            e.setdefault('city', location)
        new_events = [e for e in events if e['link'] not in existing_links]
        all_events.extend(new_events)
        existing_links.update(e['link'] for e in new_events)
        
        print(f"Added {len(new_events)} new events")
        
        await asyncio.sleep(1)  # Be nice
    
    # Save results (preserve existing and append new)
    with open(output_file, 'w') as f:
        json.dump({
            'events': all_events,
            'total': len(all_events),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n✓ Saved {len(all_events)} total events to {output_file}")
    return all_events


async def main():
    events = await scrape_eventbrite()
    print(f"\nTotal events: {len(events)}")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['date']} {e['time']}")


if __name__ == '__main__':
    from datetime import timedelta
    asyncio.run(main())
