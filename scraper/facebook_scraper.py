#!/usr/bin/env python3
"""
Facebook Events scraper - Playwright primary, Firecrawl fallback
Uses explicit numeric-ID URLs for supported cities.
For unsupported cities, tries two approaches:
  [1/2] Keyword search (city name in query, no IP dependency)
  [2/2] this_week + proxy rotation (IP-based geo-location)
Results from both are merged and deduplicated.
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
SEARCH_URL_TEMPLATE = 'https://www.facebook.com/events/search/?q={}'


def _city_code_to_search_name(code: str) -> str:
    """Convert 'dc--washington' to 'Washington DC', 'fl--miami' to 'Miami', etc."""
    special = {
        'dc--washington': 'Washington DC',
        'ny--new-york': 'New York City',
        'ca--los-angeles': 'Los Angeles',
        'ca--san-francisco': 'San Francisco',
        'ca--san-diego': 'San Diego',
        'ca--san-jose': 'San Jose',
    }
    if code in special:
        return special[code]
    parts = code.split('--', 1)
    if len(parts) == 2:
        return parts[1].replace('-', ' ').title()
    return code


def dedup_events(events: list) -> list:
    """Deduplicate events by link, keeping first occurrence."""
    seen = set()
    result = []
    for e in events:
        link = e.get('link', '')
        if link and link not in seen:
            seen.add(link)
            result.append(e)
        elif not link:
            result.append(e)
    return result


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


def _find_cards(soup) -> list:
    """Find event card containers using multiple strategies, from most to least specific."""
    strategies = [
        # 1: data-pagelet attributes (Facebook's React container pattern, fairly stable)
        lambda: soup.find_all('div', attrs={'data-pagelet': re.compile(r'Event|FeedUnit|TimelineUnit', re.I)}),
        # 2: Event links first (structural — find event <a> tags, walk up to parent card)
        lambda: _cards_from_event_links(soup),
        # 3: role="article" (semantic, stable across redesigns)
        lambda: soup.find_all(['div', 'article'], role='article'),
        # 4: aria-label containing "event" (accessibility attributes are stable)
        lambda: soup.find_all(['div', 'li', 'section'], attrs={'aria-label': re.compile(r'event', re.I)}),
        # 5: Generic list items or cards with event-like structure
        lambda: soup.find_all(['div', 'li'], class_=re.compile(r'card|tile|item|result', re.I)),
    ]
    for strategy in strategies:
        cards = strategy()
        if cards:
            print(f'  [Facebook] Strategy {strategies.index(strategy)+1}: {len(cards)} containers')
            return cards
    return []


def _cards_from_event_links(soup) -> list:
    """Find event containers by locating event links first, then walking up to parent card."""
    event_links = soup.find_all('a', href=re.compile(r'/events/\d+'))
    if not event_links:
        return []
    cards = []
    seen = set()
    for link in event_links:
        parent = link.find_parent(['div', 'li', 'section'])
        if parent and id(parent) not in seen:
            seen.add(id(parent))
            cards.append(parent)
    return cards


def _extract_event_data_from_scripts(soup) -> list:
    """Try to extract event data from embedded JSON scripts (Next.js data, JSON-LD, etc.)."""
    events = []
    for script in soup.find_all('script', type=re.compile(r'json|ld\+json', re.I)):
        try:
            import json as _json
            data = _json.loads(script.string)
            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                continue
            for item in items:
                name = item.get('name', '')
                url = item.get('url', '')
                if name and url and '/events/' in url:
                    start_date = item.get('startDate', '') or item.get('date', '')
                    location = item.get('location', {})
                    loc_name = ''
                    if isinstance(location, dict):
                        loc_name = location.get('name', '') or location.get('address', {}).get('streetAddress', '')
                    elif isinstance(location, str):
                        loc_name = location
                    events.append({
                        'title': clean_title(name),
                        'date': start_date[:10] if start_date else '',
                        'time': '',
                        'location': clean_location(loc_name),
                        'link': url.split('?')[0],
                        'description': item.get('description', ''),
                        'source': 'Facebook',
                        'city': '',
                    })
        except Exception:
            continue
    return events


def parse_events_from_html(html: str) -> list:
    """Parse Facebook Events listing page HTML using multiple strategies."""
    soup = BeautifulSoup(html, 'html.parser')
    events = []

    # Try embedded JSON data first (most reliable when present)
    events = _extract_event_data_from_scripts(soup)
    if events:
        print(f'  [Facebook] Extracted {len(events)} events from embedded JSON')
        return events

    # Find card containers using structural strategies
    cards = _find_cards(soup)
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

            card_text = card.get_text(separator=' ', strip=True)

            # Extract title from card text — Facebook dumps all text in one node
            title = ''
            raw_text = link.get_text(separator=' ', strip=True)
            if not raw_text:
                raw_text = card_text

            # Strip interested/going suffixes
            clean_raw = re.sub(
                r'\d+[\s\u00a0]*interested[\s\u00a0]*[·\u00b7\*]?[\s\u00a0]*\d+[\s\u00a0]*going',
                '', raw_text, flags=re.I
            )
            clean_raw = re.sub(r'\d+\s*interested', '', clean_raw, flags=re.I)
            clean_raw = re.sub(r'\d+\s*going', '', clean_raw, flags=re.I)

            # Remove date prefixes
            clean_raw = re.sub(
                r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*'
                r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d+'
                r'(?:\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d+)?)\s*',
                '', clean_raw, flags=re.I
            )
            clean_raw = re.sub(r'^Happening\s+now\s*', '', clean_raw, flags=re.I).strip()

            # Remove leading location-like patterns (street number prefix)
            # Title is often the segment between the date and the first address pattern
            LOCATION_SUFFIXES = r'(?:Street|Avenue|Road|Drive|Lane|Boulevard|Way|Court|Place|Circle|Sq|Blvd|Rd|Dr|Ln|Ave|St)'
            address_match = re.search(
                r'\b\d{1,6}\s+.+?\s+' + LOCATION_SUFFIXES + r'\b',
                clean_raw, re.I
            )
            if address_match:
                title = clean_raw[:address_match.start()].strip()
            else:
                # Try splitting on location patterns like "City, State"
                state_match = re.search(
                    r',\s*[A-Z]{2}\s+\d{5}(?:\s*[-–]\s*\d{4})?\s',
                    clean_raw, re.I
                )
                if state_match:
                    title = clean_raw[:state_match.start()].strip()
                else:
                    # Try comma split - title is usually before the first comma
                    parts = clean_raw.split(',', 2)
                    if len(parts) >= 2:
                        title = parts[0].strip()
                    else:
                        title = clean_raw[:80].strip()
                    # If title ends with a location suffix, strip word + suffix from title
                    suffix_match = re.search(
                        r'\s+\w+\s+' + LOCATION_SUFFIXES + r'$', title, re.I
                    )
                    if suffix_match:
                        title = title[:suffix_match.start()].strip()

            if not title or len(title) < 3:
                title = clean_raw[:80].strip()
            title = clean_title(title)
            if not title or len(title) < 3:
                continue

            date_str = ''
            time_str = 'TBA'

            # Try common date patterns in card text
            for el in card.find_all(['span', 'div', 'time']):
                dt_text = el.get_text(strip=True)
                if dt_text:
                    d, t = parse_facebook_date(dt_text)
                    if d:
                        date_str, time_str = d, t
                        break

            if not date_str:
                # Fallback: try to find date-like patterns in card text
                date_patterns = re.findall(
                    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}',
                    card_text, re.I
                )
                if date_patterns:
                    from datetime import datetime
                    month_map = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                    }
                    m = month_map.get(date_patterns[0][:3].lower())
                    d = int(re.search(r'\d+', card_text[card_text.find(date_patterns[0]):]).group())
                    if m and d:
                        from datetime import datetime as dt2
                        now = dt2.now()
                        try:
                            ed = dt2(now.year, m, d)
                            if ed.date() < now.date():
                                ed = dt2(now.year + 1, m, d)
                            date_str = ed.strftime('%Y-%m-%d')
                        except ValueError:
                            pass

            location_text = 'Location TBA'
            # Try to find location by extracting from card_text after the title
            if title and title in card_text:
                title_end = card_text.index(title) + len(title)
                after_title = card_text[title_end:].strip()
                # Clean leading punctuation/dashes
                after_title = re.sub(r'^[\s,;:\-–—]+', '', after_title)
                # Remove date remnants and interested/going
                after_title = re.sub(
                    r'\d+[\s\u00a0]*interested[\s\u00a0]*[·\u00b7\*]?[\s\u00a0]*\d+[\s\u00a0]*going.*',
                    '', after_title, flags=re.I
                )
                after_title = re.sub(r'\d+\s*interested.*', '', after_title, flags=re.I)
                after_title = re.sub(r'\d+\s*going.*', '', after_title, flags=re.I)
                if after_title.strip():
                    location_text = clean_location(after_title.strip())
            if location_text == 'Location TBA':
                for el in card.find_all(['span', 'div']):
                    text = el.get_text(strip=True)
                    if text and len(text) > 5 and len(text) < 100:
                        if any(c.isupper() for c in text) and not any(
                            w in text.lower() for w in ['interested', 'going', 'share', 'like']
                        ):
                            location_text = clean_location(text)
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

    all_events = []

    if city_code in fb_map:
        # ===== EXPLICIT CITY: single direct URL with numeric ID =====
        slug, numeric_id = fb_map[city_code]
        url = f'https://www.facebook.com/events/explore/{slug}/{numeric_id}'
        print(f'\nScraping Facebook (explicit URL): {url}')

        html = await fetch_page(url, use_firecrawl_fallback=True)
        if html:
            all_events = parse_events_from_html(html)
        else:
            print('Failed to fetch Facebook Events page')
    else:
        # ===== NON-EXPLICIT CITY: try two approaches in parallel =====
        print(f'\nScraping Facebook (city {city_code} lacks explicit numeric ID)')

        # Approach 1: City-keyword search URL (no IP dependency)
        search_name = _city_code_to_search_name(city_code)
        search_url = SEARCH_URL_TEMPLATE.format(search_name.replace(' ', '+'))
        print(f'  [1/2] Keyword search: {search_url}')

        html_kw = await fetch_page(search_url, use_firecrawl_fallback=False)

        if html_kw:
            kw_events = parse_events_from_html(html_kw)
            print(f'  [1/2] Keyword search returned {len(kw_events)} events')
            all_events.extend(kw_events)
        else:
            print('  [1/2] Keyword search failed (blocked or empty)')

        # Approach 2: this_week + proxy rotation (IP-based geo-location)
        print(f'  [2/2] this_week + proxy rotation: {DEFAULT_LISTING}')
        html_tw = await fetch_page(DEFAULT_LISTING, use_firecrawl_fallback=False)

        if not html_tw:
            print('  [2/2] Playwright failed, trying proxy rotation...')
            try:
                from proxy_fallback import retry_with_proxies
                html_tw = await retry_with_proxies(DEFAULT_LISTING, max_retries=3)
            except ImportError:
                print('  [2/2] proxy_fallback not available')
            except Exception as e:
                print(f'  [2/2] Proxy fallback error: {e}')

        if html_tw:
            tw_events = parse_events_from_html(html_tw)
            print(f'  [2/2] this_week returned {len(tw_events)} events')
            all_events.extend(tw_events)
        else:
            print('  [2/2] this_week + proxy failed')

        if not all_events:
            print('Failed to fetch Facebook Events page from both approaches')
            return []

    # Deduplicate and tag with city
    all_events = dedup_events(all_events)
    for event in all_events:
        event['city'] = city_code

    # Enrich from individual event pages when missing description or location
    for event in all_events:
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
        'events': all_events,
        'total': len(all_events),
        'last_updated': datetime.now().isoformat(),
    }

    with open(output_file, 'w') as f:
        json.dump(out_data, f, indent=2)

    print(f'[OK] Saved {len(all_events)} events to {output_file}')
    return all_events


async def main():
    events = await scrape_facebook('ny--new-york')
    print(f'\nTotal: {len(events)} events')
    for e in events[:5]:
        print(f'  - {e["title"][:50]} | {e["date"]} {e["time"]}')


if __name__ == '__main__':
    asyncio.run(main())
