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
from playwright.async_api import async_playwright


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
    """Try multiple strategies to fetch RA HTML."""
    # First try with Playwright mobile profile
    browser = None
    p = None
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
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        html = await page.content()
        await browser.close()
        await p.stop()
        return html
    except Exception as e:
        print(f"Playwright error: {e}")
        if browser:
            try:
                await browser.close()
            except:
                pass
        if p:
            try:
                await p.stop()
            except:
                pass

    # Fallback: fetch_page (Firecrawl/Hyperbrowser fallback configured in browser.py)
    html = await fetch_page(url, use_firecrawl_fallback=True)
    return html or ""


async def scrape_ra(location: str = "ca--los-angeles") -> list:
    """Scrape RA.co events for a location"""
    output_file = os.path.join(os.path.dirname(__file__), "ra_events.json")

    # Use the RA_CITIES mapping if available, otherwise fall back to manual parsing
    if location in RA_CITIES:
        country, city = RA_CITIES[location]
    else:
        # Fallback to manual parsing
        parts = location.split('--')
        if len(parts) >= 2:
            city = parts[1].replace('-', '')
        else:
            city = 'losangeles'
        country = 'us'

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
                date_elem = parent.find('span', class_=re.compile(r'Text', re.I))
                if date_elem:
                    date_text = parse_ra_date(date_elem.get_text(strip=True)) or date_elem.get_text(strip=True)
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

    # Enrich from individual event pages
    for event in events:
        needs_enrichment = (
            (event.get('description') == '') or  # Empty string instead of None check
            (event.get('date') == '') or  # Empty string instead of None check
            (event.get('location') in ("TBA", "Location TBA"))
        )
        
        if needs_enrichment:
            detail_html = await fetch_page(event['link'], use_firecrawl_fallback=True)
            if detail_html:
                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                desc_elem = detail_soup.find(class_=re.compile(r'EventDescription', re.I))
                if desc_elem and event.get('description') == '':
                    event['description'] = desc_elem.get_text(" ", strip=True)[:500]
                venue_elem = detail_soup.find(attrs={'data-pw-test-id': 'event-venue-link'})
                if venue_elem and event.get('location') in ("TBA", "Location TBA"):
                    event['location'] = venue_elem.get_text(strip=True)
                if event.get('date') == '':
                    date_elem = detail_soup.find(attrs={'data-tracking-id': 'event-detail-bar'})
                    if date_elem:
                        event['date'] = date_elem.get_text(" ", strip=True)
            await asyncio.sleep(0.3)

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

