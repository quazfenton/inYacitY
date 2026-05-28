#!/usr/bin/env python3
"""
RA.co scraper - Playwright primary, Firecrawl fallback
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from browser import fetch_page


# City mapping
RA_CITIES = {
    'ca--los-angeles': ('us', 'losangeles'),
    'ny--new-york': ('us', 'newyorkcity'),
    'fl--miami': ('us', 'miami'),
    'il--chicago': ('us', 'chicago'),
    'tx--austin': ('us', 'austin'),
    'ca--san-francisco': ('us', 'sanfrancisco'),
    'wa--seattle': ('us', 'seattle'),
    'co--denver': ('us', 'denver'),
    'ma--boston': ('us', 'boston'),
}


def parse_ra_date(date_text: str) -> str:
    """Parse 'Sat, 7 Feb' to YYYY-MM-DD."""
    if not date_text:
        return ""
    today = datetime.now()
    match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_text)
    if not match:
        return ""
    day = int(match.group(1))
    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    month = month_map.get(match.group(2))
    year = today.year
    try:
        event_date = datetime(year, month, day)
        if event_date.date() < today.date():
            event_date = datetime(year + 1, month, day)
        return event_date.strftime("%Y-%m-%d")
    except ValueError:
        return ""


async def fetch_ra_html(url: str) -> str:
    """Fetch RA HTML via fetch_page which has robust block detection + Firecrawl fallback."""
    return await fetch_page(url, use_firecrawl_fallback=True) or ""


async def scrape_ra(location: str = "ca--los-angeles") -> list:
    """Scrape RA.co events for a location"""
    output_file = os.path.join(os.path.dirname(__file__), "ra_events.json")

    # Use the RA_CITIES mapping if available
    if location not in RA_CITIES:
        print(f"⚠ RA.co: City '{location}' not supported. Skipping.")
        return []
    
    country, city = RA_CITIES[location]

    url = f"https://ra.co/events/{country}/{city}"
    print(f"\nScraping RA.co: {url}")

    html = await fetch_ra_html(url)
    if len(html) < 5000:
        print(f"Page too small ({len(html)} bytes), likely blocked")
        return []

    # Parse events
    soup = BeautifulSoup(html, 'html.parser')
    events = []

    # Find events by title link
    event_links = soup.find_all(attrs={'data-pw-test-id': 'event-title-link'})
    print(f"Found {len(event_links)} events with data-pw-test-id")

    for link_elem in event_links:
        try:
            href = link_elem.get('href', '')
            if not href:
                continue

            if not href.startswith('http'):
                href = f"https://ra.co{href}"

            title = link_elem.get_text(strip=True)
            parent = link_elem.find_parent(['li', 'article', 'div'])

            date_text = ""
            venue = "TBA"
            if parent:
                for span in parent.find_all('span', class_=re.compile(r'Text', re.I)):
                    txt = span.get_text(strip=True)
                    if re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[,.]?\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', txt):
                        date_text = parse_ra_date(txt) or txt
                        break
                venue_elem = parent.find(attrs={'data-pw-test-id': 'event-venue-link'})
                if venue_elem:
                    venue = venue_elem.get_text(strip=True)

            events.append({
                'title': title,
                'date': date_text,
                'time': '',
                'location': venue,
                'link': href,
                'description': '',
                'source': 'RA.co',
                'city': location
            })

        except Exception as e:
            print(f"Error parsing card: {e}")
            continue

    print(f"Extracted {len(events)} events")

    # Enrich from individual event pages (parallel with skip_playwright)
    enrichment_tasks = []
    for event in events:
        needs_enrichment = (
            (event.get('description') == '') or
            (event.get('date') == '') or
            (event.get('location') in ("TBA", "Location TBA"))
        )
        if needs_enrichment:
            enrichment_tasks.append(event)

    if enrichment_tasks:
        sem = asyncio.Semaphore(5)

        async def enrich_event(event):
            async with sem:
                detail_html = await fetch_page(event['link'], use_firecrawl_fallback=True, skip_playwright=True)
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    desc_elem = detail_soup.find(class_=re.compile(r'EventDescription', re.I))
                    if desc_elem and event.get('description') == '':
                        event['description'] = desc_elem.get_text(" ", strip=True)[:500]
                    venue_elem = detail_soup.find(attrs={'data-pw-test-id': 'event-venue-link'})
                    if venue_elem and event.get('location') in ("TBA", "Location TBA"):
                        event['location'] = venue_elem.get_text(strip=True)
                    if event.get('date') == '' or event.get('time') == '':
                        detail_bar = detail_soup.find(attrs={'data-tracking-id': 'event-detail-bar'})
                        if detail_bar:
                            bar_text = detail_bar.get_text(" ", strip=True)
                            if event.get('date') == '':
                                parsed = parse_ra_date(bar_text)
                                if parsed:
                                    event['date'] = parsed
                            if event.get('time') == '':
                                time_match = re.search(r'(\d{1,2}:\d{2})\s*(?:am|pm)', bar_text, re.I)
                                if not time_match:
                                    time_match = re.search(r'(\d{1,2}):(\d{2})', bar_text)
                                if time_match:
                                    h, m = int(time_match.group(1)), int(time_match.group(2))
                                    ampm = "AM" if h < 12 else "PM"
                                    if h > 12:
                                        h = h - 12
                                    elif h == 0:
                                        h = 12
                                    event['time'] = f"{h}:{m:02d} {ampm}"

        await asyncio.gather(*[enrich_event(e) for e in enrichment_tasks])

    # Save results (city-scoped)
    out_data = {'cities': {}, 'last_updated': datetime.now().isoformat()}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing = json.load(f)
                if isinstance(existing, dict) and existing.get('cities'):
                    out_data['cities'] = existing['cities']
        except:
            pass

    out_data['cities'][location] = {
        'events': events,
        'total': len(events),
        'last_updated': datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(out_data, f, indent=2)

    print(f"✓ Saved {len(events)} events to {output_file}")
    return events


async def main():
    events = await scrape_ra("ca--los-angeles")
    print(f"\nTotal: {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['link'][:50]}")


if __name__ == '__main__':
    asyncio.run(main())

