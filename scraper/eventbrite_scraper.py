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


def parse_event_date(date_str: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return ""

    today = datetime.now()
    text = date_str.strip()

    # Handle relative dates
    if "today" in text.lower():
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in text.lower():
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    # Formats like "Sat, Feb 21 • 5:00 PM", "Feb 21"
    m = re.search(
        r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?'
        r'\s*,?\s*([A-Za-z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?',
        text
    )
    if m:
        month_str, day_str, year_str = m.group(1), m.group(2), m.group(3)
        month = month_map.get(month_str.lower())
        if month:
            day = int(day_str)
            year = int(year_str) if year_str else today.year
            try:
                event_date = datetime(year, month, day)
                if event_date < today and not year_str:
                    event_date = datetime(year + 1, month, day)
                return event_date.strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Numeric formats
    for pattern in (r'(\d{1,2})/(\d{1,2})/(\d{4})', r'(\d{4})-(\d{1,2})-(\d{1,2})'):
        match = re.search(pattern, text)
        if match:
            try:
                if pattern.startswith('(\\d{1,2})'):
                    month, day, year = map(int, match.groups())
                else:
                    year, month, day = map(int, match.groups())
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

    return ""


def extract_time(date_str: str) -> str:
    """Extract time from date string."""
    if not date_str:
        return "TBA"
    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*[AP]M)', date_str, re.I)
    if time_match:
        return time_match.group(1).upper().replace(' ', '')
    return "TBA"


def clean_title(raw_title: str) -> str:
    """Clean UI prefixes from title."""
    if not raw_title:
        return ""
    title = re.sub(r'^\s*View\s+', '', raw_title, flags=re.I)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def clean_description(desc_text: str) -> str:
    if not desc_text:
        return ""
    text = re.sub(r'\s+', ' ', desc_text).strip()
    if text.lower().startswith('overview '):
        text = text[len('overview '):].strip()
    return text


def parse_card_date_time_and_location(card) -> tuple:
    """Parse date/time/location from card text blocks."""
    date_text = ""
    location = "Location TBA"

    p_tags = card.find_all('p')
    for p in p_tags:
        text = p.get_text(strip=True)
        if not text:
            continue
        if re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2}:\d{2})', text, re.I):
            if not date_text:
                date_text = text
                continue
        if location == "Location TBA" and not re.search(r'^\d{1,2}:\d{2}', text):
            if len(text) > 3 and len(text) < 120:
                location = text

    return date_text, location


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

            title = clean_title(title)
            if not title:
                continue

            # Get date/time
            date_elem = card.find(attrs={'data-testid': re.compile(r'date|time', re.I)})
            date_text = date_elem.get_text(strip=True) if date_elem else ""

            if not date_text:
                date_text, _ = parse_card_date_time_and_location(card)

            if not date_text:
                date_match = re.search(r'([A-Za-z]+,\s*[A-Za-z]+\s+\d{1,2}[^\n]*)', card.get_text())
                if date_match:
                    date_text = date_match.group(1).strip()

            # Parse date and time
            event_date = parse_event_date(date_text)
            event_time = extract_time(date_text)

            # Get location
            location = "Location TBA"
            location_elem = card.find(attrs={'data-testid': re.compile(r'location|venue', re.I)})
            if location_elem:
                location = location_elem.get_text(strip=True)
            else:
                _, location = parse_card_date_time_and_location(card)
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

    output_file = os.path.join(os.path.dirname(__file__), "eventbrite_events.json")

    # Load existing events (city-scoped)
    existing_links = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                if 'cities' in data:
                    existing_links = {e.get('link', '') for e in data['cities'].get(location, {}).get('events', [])}
                else:
                    existing_links = {e.get('link', '') for e in data.get('events', [])}
            print(f"Loaded {len(existing_links)} existing events for {location}")
        except:
            pass

    all_events = []
    base_url = eb_config.get('base_url', 'https://www.eventbrite.com/d/{location}/free--events/').format(location=location)

    empty_pages = 0

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
        new_events = [e for e in events if e['link'] not in existing_links]
        for e in new_events:
            e['city'] = location
        all_events.extend(new_events)
        existing_links.update(e['link'] for e in new_events)

        print(f"Added {len(new_events)} new events")

        if not new_events:
            empty_pages += 1
        else:
            empty_pages = 0

        if empty_pages >= 2:
            print("No new events on consecutive pages, stopping early.")
            break

        await asyncio.sleep(1)  # Be nice

    # Enrich with event page details when missing data
    for event in all_events:
        if (not event.get('date')) or event.get('time') == "TBA" or event.get('location') == "Location TBA" or not event.get('description'):
            detail = await fetch_page(event['link'], use_firecrawl_fallback=True)
            if detail:
                detail_soup = BeautifulSoup(detail, 'html.parser')
                if not event.get('title'):
                    title_elem = detail_soup.find('h1', attrs={'data-testid': 'event-title'})
                    if title_elem:
                        event['title'] = clean_title(title_elem.get_text(strip=True))
                if not event.get('date') or event.get('time') == "TBA":
                    date_elem = detail_soup.find(attrs={'data-testid': 'conversion-bar-date'})
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        parsed_date = parse_event_date(date_text)
                        if parsed_date:
                            event['date'] = parsed_date
                        event['time'] = extract_time(date_text)
                if event.get('location') == "Location TBA":
                    loc_elem = detail_soup.find(attrs={'data-testid': 'event-venue'})
                    if loc_elem:
                        event['location'] = loc_elem.get_text(strip=True)
                if not event.get('description'):
                    desc_elem = detail_soup.select_one('div[data-testid="section-wrapper-overview"]') or detail_soup.select_one('.Overview_summary__kcVOq')
                    if desc_elem:
                        desc_text = desc_elem.get_text(" ", strip=True)
                        event['description'] = clean_description(desc_text)[:500]
            await asyncio.sleep(0.5)

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
        'events': all_events,
        'total': len(all_events),
        'last_updated': datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(out_data, f, indent=2)

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

