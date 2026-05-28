#!/usr/bin/env python3
"""
Facebook Events scraper - Playwright primary, Firecrawl fallback
Uses explicit numeric-ID URLs for supported cities; defaults to
this_week + proxy rotation for unsupported cities.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from browser import fetch_page
from config_loader import get_config

FACEBOOK_CITY_MAP = {
    'ca--los-angeles': ('us-los-angeles', '110970792260960'),
    'ca--san-francisco': ('us-san-francisco', '114952118516947'),
    'ga--atlanta': ('us-atlanta', '107991659233606'),
    'nv--las-vegas': ('us-las-vegas', '108081209214649'),
    'ny--new-york': ('us-new-york', '108424279189115'),
    'tx--houston': ('us-houston', '115963528414384'),
    'wa--seattle': ('us-seattle', '110843418940484'),
}

DEFAULT_LISTING = 'https://www.facebook.com/events/explore/this_week'


def parse_facebook_date(text: str) -> tuple:
    """Parse Facebook date/time text to (date, time)."""
    if not text:
        return ('', '')
    today = datetime.now()
    text = text.strip()

    if 'today' in text.lower():
        date_str = today.strftime('%Y-%m-%d')
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*[AP]M)', text, re.I)
        time_str = time_match.group(1).upper().replace(' ', '') if time_match else 'TBA'
        return (date_str, time_str)

    if 'tomorrow' in text.lower():
        from datetime import timedelta
        date_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*[AP]M)', text, re.I)
        time_str = time_match.group(1).upper().replace(' ', '') if time_match else 'TBA'
        return (date_str, time_str)

    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    }

    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})', text, re.I)
    if match:
        month = month_map.get(match.group(1).lower())
        day = int(match.group(2))
        year = today.year
        try:
            event_date = datetime(year, month, day)
            if event_date.date() < today.date():
                event_date = datetime(year + 1, month, day)
            date_str = event_date.strftime('%Y-%m-%d')
        except ValueError:
            date_str = ''
    else:
        date_str = ''

    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*[AP]M)', text, re.I)
    time_str = time_match.group(1).upper().replace(' ', '') if time_match else 'TBA'

    return (date_str, time_str)


def clean_title(raw: str) -> str:
    if not raw:
        return ''
    return re.sub(r'\s+', ' ', raw).strip()


def clean_location(text: str) -> str:
    if not text:
        return 'Location TBA'
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned or 'Location TBA'


def parse_events_from_html(html: str) -> list:
    """Parse Facebook Events listing page HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    events = []

    # Facebook event cards — try multiple selector strategies
    cards = (
        soup.find_all('div', class_=re.compile(r'x1yztbdb', re.I))
        or soup.find_all('div', attrs={'data-pagelet': re.compile(r'Event', re.I)})
        or soup.find_all('div', class_=re.compile(r'event', re.I))
        or soup.find_all('div', role='article')
    )

    if not cards:
        cards = soup.find_all('div', class_=re.compile(r'x1c4vz4f', re.I))

    print(f'  [Facebook] Found {len(cards)} potential event containers')

    for card in cards:
        try:
            link = card.find('a', href=re.compile(r'/events/\d+|/event'))
            if not link:
                continue

            href = link.get('href', '')
            if href.startswith('/'):
                href = 'https://www.facebook.com' + href
            href = href.split('?')[0]

            title = ''
            title_elem = card.find(['h2', 'h3', 'h4', 'span', 'strong'],
                                    class_=re.compile(r'title|name|heading', re.I))
            if title_elem:
                title = clean_title(title_elem.get_text(strip=True))
            if not title:
                title = clean_title(link.get_text(strip=True))
            if not title or len(title) < 3:
                continue

            card_text = card.get_text(separator=' ', strip=True)

            date_str = ''
            time_str = 'TBA'

            date_elem = card.find('span', class_=re.compile(r'date|time', re.I))
            if date_elem:
                dt_text = date_elem.get_text(strip=True)
                date_str, time_str = parse_facebook_date(dt_text)

            if not date_str:
                for cls in ['x1ve1l4p', 'x1rg5ohu', 'x1n2onr6']:
                    el = card.find('span', class_=re.compile(cls))
                    if el:
                        date_str, time_str = parse_facebook_date(el.get_text(strip=True))
                        break

            location_text = 'Location TBA'
            loc_elem = card.find('span', class_=re.compile(r'location|venue|place', re.I))
            if loc_elem:
                location_text = clean_location(loc_elem.get_text(strip=True))
            if location_text == 'Location TBA':
                parts = card_text.split(' · ')
                for part in parts:
                    if any(c.isupper() for c in part) and len(part) > 5 and len(part) < 100:
                        if 'interested' not in part.lower() and 'going' not in part.lower():
                            location_text = clean_location(part)
                            break

            events.append({
                'title': title,
                'date': date_str,
                'time': time_str,
                'location': location_text,
                'link': href,
                'description': '',
                'source': 'Facebook',
                'city': '',
            })

        except Exception as e:
            print(f'  [Facebook] Error parsing card: {e}')
            continue

    print(f'  [Facebook] Extracted {len(events)} events')
    return events


async def scrape_facebook(city: str = None) -> list:
    """Scrape Facebook Events for a city."""
    config = get_config()

    city_code = None
    if not city:
        city_code = config.get_location()
    else:
        city_code = city

    fb_config = config.get_scraper_config('FACEBOOK')
    fb_map = fb_config.get('city_map', FACEBOOK_CITY_MAP)

    output_file = os.path.join(os.path.dirname(__file__), 'facebook_events.json')

    # Build URL
    if city_code in fb_map:
        slug, numeric_id = fb_map[city_code]
        url = f'https://www.facebook.com/events/explore/{slug}/{numeric_id}'
        print(f'\nScraping Facebook (explicit URL): {url}')
    else:
        url = DEFAULT_LISTING
        print(f'\nScraping Facebook (default this_week): {url}')
        print(f'  City {city_code} lacks explicit FB numeric ID, using this_week + proxy rotation')

    html = await fetch_page(url, use_firecrawl_fallback=True)

    # If empty and city not in explicit map, try proxy rotation for location-aware results
    if not html and city_code not in fb_map:
        print('  [Facebook] Fetch failed, trying proxy rotation for location-aware results...')
        try:
            from proxy_fallback import retry_with_proxies
            html = await retry_with_proxies(url, max_retries=3)
        except ImportError:
            print('  [Facebook] proxy_fallback not available')
        except Exception as e:
            print(f'  [Facebook] Proxy fallback error: {e}')

    if not html:
        print('Failed to fetch Facebook Events page')
        return []

    events = parse_events_from_html(html)
    for event in events:
        event['city'] = city_code

    # Enrich from individual event pages when missing description or location
    for event in events:
        if not event.get('description') or event.get('location') == 'Location TBA':
            detail_html = await fetch_page(event['link'], use_firecrawl_fallback=True, skip_playwright=True)
            if detail_html:
                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                if not event.get('description'):
                    desc_el = detail_soup.find('div', class_=re.compile(r'description|body|content', re.I))
                    if desc_el:
                        event['description'] = re.sub(r'\s+', ' ', desc_el.get_text(strip=True))[:500]
                if event.get('location') == 'Location TBA':
                    loc_el = detail_soup.find('span', class_=re.compile(r'location|venue|place', re.I))
                    if loc_el:
                        event['location'] = clean_location(loc_el.get_text(strip=True))
        await asyncio.sleep(0.3)

    # Save results (city-scoped)
    out_data = {'cities': {}, 'last_updated': datetime.now().isoformat()}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing = json.load(f)
                if isinstance(existing, dict) and existing.get('cities'):
                    out_data['cities'] = existing['cities']
        except Exception:
            pass

    out_data['cities'][city_code] = {
        'events': events,
        'total': len(events),
        'last_updated': datetime.now().isoformat(),
    }

    with open(output_file, 'w') as f:
        json.dump(out_data, f, indent=2)

    print(f'[OK] Saved {len(events)} events to {output_file}')
    return events


async def main():
    events = await scrape_facebook('ny--new-york')
    print(f'\nTotal: {len(events)} events')
    for e in events[:5]:
        print(f'  - {e["title"][:50]} | {e["date"]} {e["time"]}')


if __name__ == '__main__':
    asyncio.run(main())
