#!/usr/bin/env python3
"""
Accurate script to scrape free events from Eventbrite
"""

import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import os
import json
from typing import Dict, List, Optional
import aiohttp
from simple_browser import create_browser, close_browser


def load_config() -> Dict:
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


CONFIG = load_config()


async def safe_wait(page, milliseconds: int):
    if hasattr(page, 'wait_for_timeout'):
        await page.wait_for_timeout(milliseconds)
    else:
        await asyncio.sleep(milliseconds / 1000)


FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
HYPERBROWSER_API_KEY = os.environ.get("HYPERBROWSER_API_KEY")


async def fetch_with_firecrawl(url: str) -> Optional[str]:
    if not FIRECRAWL_API_KEY or not CONFIG.get("FALLBACKS", {}).get("ENABLE_FIRECRAWL_FALLBACK", False):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "url": url,
                "render": True,
                "mode": "scrape",
                "maxAge": 0
            }
            async with session.post(
                "https://api.firecrawl.dev/v2/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    print(f"Firecrawl returned status {resp.status} for {url}")
                    return None
                data = await resp.json()
                for key in ("html", "content", "page", "body", "scrape"):
                    candidate = data.get(key)
                    if isinstance(candidate, dict):
                        candidate = candidate.get("html") or candidate.get("content")
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate
    except Exception as exc:
        print(f"Firecrawl fallback failed: {exc}")
    return None


async def fetch_with_hyperbrowser(url: str, instructions: str = None) -> Optional[str]:
    if not HYPERBROWSER_API_KEY or not CONFIG.get("FALLBACKS", {}).get("ENABLE_HYPERBROWSER_FALLBACK", False):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "url": url,
                "instructions": instructions or "Render the page, solve any captchas, and return the full HTML content in the `content` field.",
                "solve_captcha": True,
                "capture": "html"
            }
            headers = {
                "Authorization": f"Bearer {HYPERBROWSER_API_KEY}",
                "Content-Type": "application/json"
            }
            async with session.post(
                "https://api.hyperbrowser.ai/v1/browser",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    print(f"Hyperbrowser returned status {resp.status} for {url}")
                    return None
                data = await resp.json()
                for key in ("content", "html", "result", "data"):
                    candidate = data.get(key)
                    if isinstance(candidate, dict):
                        candidate = candidate.get("content") or candidate.get("html")
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate
    except Exception as exc:
        print(f"Hyperbrowser fallback failed: {exc}")
    return None


async def fetch_fallback_html(url: str) -> Optional[str]:
    html = await fetch_with_firecrawl(url)
    if html:
        return html
    return await fetch_with_hyperbrowser(url)


def format_event_time_12h(time_str: Optional[str]) -> str:
    if not time_str:
        return "TBA"
    try:
        parsed = datetime.strptime(time_str, "%H:%M")
        return parsed.strftime("%-I:%M %p")
    except ValueError:
        return time_str


def format_eventbrite_location(raw_event: Dict) -> str:
    venue = raw_event.get("primary_venue") or raw_event.get("venue") or raw_event.get("location")
    location_parts = []

    if isinstance(venue, dict):
        name = venue.get("name")
        if name:
            location_parts.append(name)
        area = venue.get("localized_area_display") or venue.get("localized_address_display")
        if area:
            location_parts.append(area)
        address_lines = venue.get("localized_multi_line_address_display")
        if isinstance(address_lines, list):
            location_parts.extend(address_lines)
        elif isinstance(address_lines, str):
            location_parts.append(address_lines)
    elif isinstance(venue, str):
        location_parts.append(venue)

    if not location_parts:
        location_name = None
        location_data = raw_event.get("location")
        if isinstance(location_data, dict):
            location_name = location_data.get("name")
        if location_name:
            location_parts.append(location_name)

    if location_parts:
        return " · ".join(location_parts)

    return "Location TBA"


def build_event_from_server_data(raw_event: Dict, existing_links: set) -> Optional[Dict]:
    link = raw_event.get("url")
    if not link or link in existing_links:
        return None

    title = raw_event.get("name") or raw_event.get("summary") or "Event Title Unknown"
    date_str = raw_event.get("start_date")
    if not date_str:
        return None

    try:
        event_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        event_date = datetime.now().date()

    time_str = format_event_time_12h(raw_event.get("start_time"))
    location = format_eventbrite_location(raw_event)
    description = raw_event.get("summary") or raw_event.get("full_description") or "Description not available"
    if description:
        description = re.sub(r'\s+', ' ', description).strip()
        if len(description) > 300:
            description = description[:300] + "..."

    return {
        'title': title,
        'link': link,
        'date': event_date,
        'time': time_str,
        'location': location,
        'description': description,
    }


def extract_eventbrite_json_results(soup) -> List[Dict]:
    marker = "window.__SERVER_DATA__ = "

    for script in soup.find_all('script'):
        script_text = script.string or script.get_text()
        if not script_text or marker not in script_text:
            continue

        payload = script_text.split(marker, 1)[1].strip()
        if payload.endswith(";"):
            payload = payload[:-1]

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        events_data = (
            data.get("search_data", {})
                .get("events", {})
                .get("results")
        )

        if isinstance(events_data, list) and events_data:
            return events_data

    return []


def convert_eventbrite_json_results(results: List[Dict], existing_links: set) -> List[Dict]:
    parsed_events = []
    max_events = CONFIG.get("MAX_EVENTS_PER_PAGE", len(results))

    for raw_event in results:
        if len(parsed_events) >= max_events:
            break

        event_info = build_event_from_server_data(raw_event, existing_links)
        if event_info:
            parsed_events.append(event_info)
            existing_links.add(event_info['link'])

    return parsed_events


def parse_event_date(date_str: str) -> datetime:
    """Parse event date string to datetime object."""
    # Clean up the date string
    date_str = date_str.strip()

    # Handle relative dates like "Tomorrow", "This week", etc.
    today = datetime.now()
    
    if "Today" in date_str or "today" in date_str:
        return today.date()
    elif "Tomorrow" in date_str or "tomorrow" in date_str:
        return (today + timedelta(days=1)).date()
    elif "This week" in date_str or "this week" in date_str:
        # Find the next occurrence of the day mentioned
        day_match = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})', date_str)
        if day_match:
            month_name, day_num = day_match.groups()
            year = today.year
            # Parse the month and day
            date_part = f"{month_name} {day_num}, {year}"
            try:
                parsed_date = datetime.strptime(date_part, "%B %d, %Y").date()
                # If the date is in the past, it might be next year
                if parsed_date < today.date():
                    parsed_date = datetime.strptime(date_part.replace(str(year), str(year + 1)), "%B %d, %Y").date()
                return parsed_date
            except ValueError:
                try:
                    parsed_date = datetime.strptime(date_part.replace(" ", " "), "%B %d, %Y").date()
                    if parsed_date < today.date():
                        parsed_date = datetime.strptime(date_part.replace(str(year), str(year + 1)), "%B %d, %Y").date()
                    return parsed_date
                except ValueError:
                    pass

    # Try to parse as full date
    date_patterns = [
        "%a, %b %d, %Y",
        "%A, %B %d, %Y", 
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%m-%d-%Y"
    ]
    
    for pattern in date_patterns:
        try:
            return datetime.strptime(date_str.split('(')[0].strip(), pattern).date()
        except ValueError:
            continue

    # If all parsing fails, return today's date as fallback
    return today.date()


def format_date_for_header(date_obj: datetime.date) -> str:
    """Format date as 'Day, Month Date, Year' for markdown header."""
    return date_obj.strftime("%A, %B %d, %Y")


async def scrape_event_description(page, event_link: str) -> str:
    """
    Scrape the description from an individual event page.
    """
    try:
        # Navigate to the event page
        await page.goto(event_link, wait_until="networkidle", timeout=15000)

        # Wait for content to load
        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
            await page.wait_for_timeout(3000)
        else:  # For pydoll Tab objects
            await asyncio.sleep(3.0)

        # Get page content
        if hasattr(page, 'content'):  # For Playwright-based browsers
            content = await page.content()
        else:  # For pydoll Tab objects
            result = await page.execute_script("return document.documentElement.outerHTML")
            # Handle potential dict response from pydoll
            if isinstance(result, dict) and 'result' in result:
                content = result['result']
            elif isinstance(result, dict) and 'value' in result:
                content = result['value']
            elif isinstance(result, str):
                content = result
            else:
                content = str(result) if result is not None else ""
        soup = BeautifulSoup(content, 'html.parser')

        # Look for description in various possible locations
        description = ""

        # Look for the summary div
        summary_div = soup.find('div', class_='summary')
        if summary_div:
            description = summary_div.get_text(strip=True)

        # If not found, look for other common description containers
        if not description:
            desc_selectors = [
                'div[data-testid="event-description"]',
                'div[itemprop="description"]',
                '.event-description',
                '.listing-description',
                '[data-automation="listing-event-description"]'
            ]

            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break

        # Clean up the description
        if description:
            # Remove extra whitespace and newlines
            description = re.sub(r'\s+', ' ', description)
            # Limit length to avoid overly long descriptions
            if len(description) > 300:
                description = description[:300] + "..."

        return description if description else "Description not available"

    except Exception as e:
        print(f"Error scraping description for {event_link}: {e}")
        return "Description not available"


async def scrape_eventbrite_page(url: str, existing_links: set = None) -> List[Dict]:
    """
    Scrape a single Eventbrite page for event information.
    """
    if existing_links is None:
        existing_links = set()
    events = []

    browser = None
    
    try:
        browser, page = await create_browser(headless=True)
        print(f"🌐 Using simple browser")

        print(f"Accessing {url}")
        
        # Simple navigation
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)  # Wait for JS to load

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        server_data_results = extract_eventbrite_json_results(soup)
        if server_data_results:
            print(f"Found {len(server_data_results)} events inside server JSON data")
            json_events = convert_eventbrite_json_results(server_data_results, existing_links)
            if json_events:
                events.extend(json_events)
                return events

        # Find event cards using the actual structure from the debug output
        event_cards = soup.find_all('div', class_='event-card')

        if not server_data_results and not event_cards:
            fallback_html = await fetch_fallback_html(url)
            if fallback_html:
                print("Fallback HTML retrieved from Firecrawl/Hyperbrowser")
                soup = BeautifulSoup(fallback_html, 'html.parser')
                server_data_results = extract_eventbrite_json_results(soup)
                if server_data_results:
                    print(f"Found {len(server_data_results)} events inside fallback server JSON data")
                    json_events = convert_eventbrite_json_results(server_data_results, existing_links)
                    if json_events:
                        events.extend(json_events)
                        return events
                event_cards = soup.find_all('div', class_='event-card')
                print(f"Fallback produced {len(event_cards)} event cards")

        print(f"Found {len(event_cards)} event cards")

        for i, card in enumerate(event_cards[:CONFIG["MAX_EVENTS_PER_PAGE"]]):
            try:
                print(f"Processing event {i+1}/{min(len(event_cards), CONFIG['MAX_EVENTS_PER_PAGE'])}")

                # Extract the event link
                link_elem = card.find('a', class_='event-card-link')
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        link = "https://www.eventbrite.com" + href
                    else:
                        link = href
                else:
                    link = "N/A"

                # Extract title - look for h3 with specific classes
                title_elem = card.find('h3', class_=re.compile(r'.*event-card__clamp.*', re.I))
                if not title_elem:
                    # Try other common title selectors
                    title_elem = card.find('h3', class_=re.compile(r'Typography.*', re.I))
                if not title_elem:
                    # Try any h3 inside the card
                    title_elem = card.find('h3')

                if title_elem:
                    # Clean up the title by removing extra text
                    raw_title = title_elem.get_text(strip=True)
                    # Remove common UI elements from the title
                    title = re.sub(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', '', raw_title, flags=re.IGNORECASE).strip()
                    # Remove leading/trailing punctuation
                    title = re.sub(r'^[-\s·]+|[-\s·]+$', '', title)
                else:
                    title = "Event Title Unknown"

                if not title or len(title.strip()) < 3:  # Skip if no meaningful title
                    continue

                # Extract date and time information
                # Look for elements with date/time information
                # First, try to find the element that contains actual date/time info (not urgency signals)
                time_elem = None
                all_p_tags = card.find_all('p', class_=re.compile(r'.*body-md.*', re.I))
                for p_tag in all_p_tags:
                    text = p_tag.get_text(strip=True)
                    # Look for text that contains actual date/time info (contains day names, months, or time formats)
                    if re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2}:\d{2})', text, re.IGNORECASE):
                        # Make sure it's not an urgency signal
                        if not re.search(r'Almost full|Sales end soon|Going fast', text, re.IGNORECASE):
                            time_elem = p_tag
                            break

                if time_elem:
                    date_time_str = time_elem.get_text(strip=True)
                    print(f"Date/time string found: {date_time_str}")  # Debugging

                    # Extract date portion - more comprehensive regex
                    date_match = re.search(r'([A-Z][a-z]+,\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|[A-Z][a-z]+\s+\d{1,2}\s*-\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4})', date_time_str)
                    if date_match:
                        date_str = date_match.group(1)
                        event_date = parse_event_date(date_str)
                    else:
                        # Look for simpler date patterns
                        simple_date_match = re.search(r'([A-Z][a-z]+ \d{1,2})', date_time_str)
                        if simple_date_match:
                            # Add current year to the date
                            date_with_year = simple_date_match.group(1) + f", {datetime.now().year}"
                            event_date = parse_event_date(date_with_year)
                        else:
                            # Check for relative dates like "Tomorrow", "Today", "This week"
                            # Look for day followed by time (e.g., "Tomorrow • 6:00 PM")
                            day_time_match = re.search(r'(Tomorrow|Today|[A-Z][a-z]+)\s*•?\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}(?:AM|PM|am|pm))', date_time_str, re.IGNORECASE)
                            if day_time_match:
                                day_part = day_time_match.group(1).lower()
                                time_part = day_time_match.group(2)

                                if "tomorrow" in day_part:
                                    event_date = (datetime.now() + timedelta(days=1)).date()
                                elif "today" in day_part:
                                    event_date = datetime.now().date()
                                else:
                                    # Try to find the next occurrence of this day
                                    target_day = day_part.capitalize()
                                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                                    if target_day in days:
                                        target_idx = days.index(target_day)
                                        current_idx = datetime.now().weekday()
                                        days_ahead = target_idx - current_idx
                                        if days_ahead <= 0:  # Target day already happened this week
                                            days_ahead += 7
                                        event_date = (datetime.now() + timedelta(days_ahead)).date()
                                    else:
                                        event_date = datetime.now().date()
                                time_str = "TBA"
                else:
                    event_date = datetime.now().date()
                    time_str = "TBA"

                # Extract location information
                # Look for elements containing location information
                location_elem = None
                # First, look for elements that contain location-related keywords but not urgency signals
                all_p_tags = card.find_all('p', class_=re.compile(r'.*body-md.*', re.I))
                for p_tag in all_p_tags:
                    text = p_tag.get_text(strip=True)
                    # Skip if this is an urgency signal like "Almost full", "Sales end soon", etc.
                    if not re.search(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', text, re.IGNORECASE):
                        if re.search(r'Washington|DC|District of Columbia|Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Venue|Building|Place|Square|Court|Lane|Circle|Drive|Boulevard|Blvd', text, re.IGNORECASE):
                            location_elem = p_tag
                            break

                if location_elem:
                    location = location_elem.get_text(strip=True)
                    # Clean up location text
                    location = re.sub(r'^[-\s·]+|[-\s·]+$', '', location)
                    # Remove urgency signals that might have slipped through
                    location = re.sub(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', '', location, flags=re.IGNORECASE).strip()
                else:
                    location = "Location TBA"

                # Check if event is free - look for "Free" text in the card
                price_elem = card.find('p', string=re.compile(r'Free|FREE|\$0', re.IGNORECASE))
                if not price_elem:
                    # Also check for elements with price wrapper classes
                    price_wrapper = card.find(class_=re.compile(r'.*priceWrapper.*', re.I))
                    if price_wrapper:
                        price_elem = price_wrapper.find('p', string=re.compile(r'Free|FREE|\$0', re.IGNORECASE))

                is_free = bool(price_elem)

                # Scrape description from the event page if it's a free event
                description = "Description not available"
                if is_free and link != "N/A" and link != "https://www.eventbrite.com":  # Only scrape description for valid free events
                    description = await scrape_event_description(page, link)
                    print(f"DEBUG: Found description for {title[:30]}...: {description[:100]}...")  # Print description to terminal

                # Early check to skip if the event link already exists in the existing file
                if link in existing_links:
                    print(f"Skipped already existing event: {title[:50]}...")
                    continue

                # Check if this event link already exists in the current events list
                if link in [evt['link'] for evt in events]:
                    print(f"Skipped duplicate event in current run: {title[:50]}...")
                    continue

                # Skip if not free
                if not is_free:
                    print(f"Skipped paid event: {title[:50]}...")
                    continue

                # Only process the event if it's free and not a duplicate
                event_info = {
                    'title': title,
                    'link': link,
                    'date': event_date,
                    'time': time_str,
                    'location': location,
                    'description': description
                }
                events.append(event_info)
                
                # Only apply interesting filter for printing, not for inclusion
                if is_interesting_event(title, location):
                    print(f"Added interesting event: {title[:50]}...")
                else:
                    print(f"Added event (not marked as interesting): {title[:50]}...")

            except Exception as e:
                print(f"Error processing event element {i}: {e}")
                continue

    except Exception as e:
        print(f"Error scraping page {url}: {e}")
    finally:
        if browser:
            await close_browser(browser)
        return events


def is_interesting_event(title: str, location: str) -> bool:
    """
    Determine if an event is interesting based on keywords.
    """
    title_lower = title.lower()
    location_lower = location.lower()
    
    # Keywords for interesting events
    interesting_keywords = [
        'comedy', 'film', 'movie', 'poetry', 'open mic', 'trivia', 'live music',
        'salsa', 'dancing', 'networking', 'party', 'festival', 'theme',
        'concert', 'theater', 'gallery', 'museum', 'workshop', 'meetup',
        'game', 'karaoke', 'wine', 'beer', 'food', 'culture', 'arts',
        'music', 'dance', 'book', 'literature', 'tech', 'startup', 'young', 'adult'
    ]
    
    # Keywords for interesting venues
    interesting_venues = [
        'eaton', 'pocket', 'drum city', '9:30', 'black cat', 'merriweather',
        'lincoln theater', 'u street', 'union station', 'the wharf', 'theater'
    ]
    
    # Check if title contains interesting keywords
    for keyword in interesting_keywords:
        if keyword in title_lower:
            return True
    
    # Check if location contains interesting venues
    for venue in interesting_venues:
        if venue in location_lower:
            return True
    
    # Prioritize events that sound like social/cultural activities
    if any(word in title_lower for word in ['social', 'cultural', 'community', 'young', 'adult']):
        return True
    
    return False


def get_eventbrite_urls() -> List[str]:
    """
    Generate URLs for Eventbrite search pages based on configuration.
    """
    location = CONFIG["LOCATION"]

    # Determine if we should include paid events
    event_type = "events" if CONFIG["MODES"]["INCLUDE_PAID_EVENTS"] else "free--events"
    base_url = f"https://www.eventbrite.com/d/{location}/{event_type}/"

    urls = []

    # Add main pages
    for page in range(1, CONFIG["MAIN_PAGES"] + 1):
        urls.append(base_url + f"?page={page}")

    # Add filtered pages based on configuration
    for filter_type in CONFIG["FILTERS_TO_USE"]:
        for page in range(1, CONFIG["FILTER_PAGES"] + 1):
            urls.append(f"https://www.eventbrite.com/d/{location}/{event_type}--{filter_type}/?page={page}")

    # If custom search terms are provided, add those URLs
    if CONFIG["MODES"]["CUSTOM_SEARCH_TERMS"]:
        for search_term in CONFIG["MODES"]["CUSTOM_SEARCH_TERMS"]:
            # Format search term for URL (replace spaces with dashes)
            formatted_term = search_term.replace(" ", "-").lower()
            for page in range(1, CONFIG["MAIN_PAGES"] + 1):
                urls.append(f"https://www.eventbrite.com/d/{location}/{formatted_term}/?page={page}")

    return urls


def format_events_for_markdown(events: List[Dict], existing_content: str) -> str:
    """
    Format events into markdown format matching the existing structure.
    """
    if not events:
        return ""

    # Group events by date
    events_by_date = {}
    for event in events:
        date_key = event['date']
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(event)

    # Check if we need to update the "Last Updated" line
    today = datetime.now().strftime("%B %d, %Y")
    updated_content = re.sub(
        r'\*Last Updated:.*\*',
        f'*Last Updated: {today}*',
        existing_content
    )

    # Sort dates
    sorted_dates = sorted(events_by_date.keys())

    for date_key in sorted_dates:
        date_header = format_date_for_header(date_key)

        # Check if this date section already exists in the document
        date_section_exists = f"## {date_header}" in existing_content

        if date_section_exists:
            # If the date section exists, append to it
            updated_content = append_events_to_existing_date(updated_content, date_key, events_by_date[date_key])
        else:
            # If the date section doesn't exist, add it
            updated_content = add_new_date_section(updated_content, date_key, events_by_date[date_key])

    return updated_content


def append_events_to_existing_date(content: str, date_key: datetime.date, events: List[Dict]) -> str:
    """
    Append new events to an existing date section in the content.
    """
    date_header = format_date_for_header(date_key)

    # Categorize events as evening or daytime based on time
    evening_events = []
    daytime_events = []
    
    for event in events:
        # Simple heuristic: events after 5 PM are evening, before 5 PM are daytime
        time_str = event['time'].upper()
        if time_str == "TBA":
            # Default to evening if time is not specified
            evening_events.append(event)
        elif "AM" in time_str:
            # Morning events
            hour_match = re.search(r'(\d{1,2}):', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                if hour >= 6 and hour <= 11:  # 6 AM to 11 AM
                    daytime_events.append(event)
                else:  # 12 AM to 5 AM (early morning)
                    evening_events.append(event)
            else:
                daytime_events.append(event)
        elif "PM" in time_str:
            # Afternoon/Evening events
            hour_match = re.search(r'(\d{1,2}):', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                if hour >= 1 and hour <= 5:  # 1 PM to 5 PM
                    daytime_events.append(event)
                else:  # 6 PM to 12 PM (evening/night)
                    evening_events.append(event)
            else:
                evening_events.append(event)
        else:
            # If no AM/PM indicator, default to evening
            evening_events.append(event)

    # Add daytime events to existing section if any exist
    if daytime_events:
        # Find the ### Daytime Events section or create it
        daytime_section_pattern = f"(## {date_header}\\s+### Daytime Events\\s+)"
        daytime_match = re.search(daytime_section_pattern, content)
        
        if daytime_match:
            # Daytime section exists, append to it
            new_daytime_events = ""
            for event in daytime_events:
                new_daytime_events += format_single_event(event)

            content = re.sub(
                f"(## {re.escape(date_header)}\\s+### Daytime Events\\s+)",
                f"\\g<1>{new_daytime_events}",
                content,
                count=1
            )
        else:
            # Daytime section doesn't exist, add it after the date header
            new_daytime_section = f"### Daytime Events\n\n"
            for event in daytime_events:
                new_daytime_section += format_single_event(event)

            content = re.sub(
                f"(## {re.escape(date_header)}\\s+)",
                f"\\g<1>{new_daytime_section}",
                content,
                count=1
            )

    # Add evening events to existing section if any exist
    if evening_events:
        # Find the ### Evening Events section or create it
        evening_section_pattern = f"(## {date_header}\\s+### Evening Events\\s+)"
        evening_match = re.search(evening_section_pattern, content)

        if evening_match:
            # Evening section exists, append to it
            new_evening_events = ""
            for event in evening_events:
                new_evening_events += format_single_event(event)

            content = re.sub(
                f"(## {re.escape(date_header)}\\s+### Evening Events\\s+)",
                f"\\g<1>{new_evening_events}",
                content,
                count=1
            )
        else:
            # Evening section doesn't exist, add it
            new_evening_section = f"### Evening Events\n\n"
            for event in evening_events:
                new_evening_section += format_single_event(event)

            # Check if there's already a daytime section
            if daytime_events:
                # Add evening section after daytime section
                content = re.sub(
                    f"(## {re.escape(date_header)}[^#]*### Daytime Events[^#]*)",
                    f"\\g<1>\n{new_evening_section}",
                    content,
                    count=1
                )
            else:
                # Add evening section after date header
                content = re.sub(
                    f"(## {re.escape(date_header)}\\s+)",
                    f"\\g<1>{new_evening_section}",
                    content,
                    count=1
                )

    return content


def add_new_date_section(content: str, date_key: datetime.date, events: List[Dict]) -> str:
    """
    Add a new date section with events to the content.
    """
    date_header = format_date_for_header(date_key)

    # Categorize events as evening or daytime based on time
    evening_events = []
    daytime_events = []
    
    for event in events:
        # Simple heuristic: events after 5 PM are evening, before 5 PM are daytime
        time_str = event['time'].upper()
        if time_str == "TBA":
            # Default to evening if time is not specified
            evening_events.append(event)
        elif "AM" in time_str:
            # Morning events
            hour_match = re.search(r'(\d{1,2}):', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                if hour >= 6 and hour <= 11:  # 6 AM to 11 AM
                    daytime_events.append(event)
                else:  # 12 AM to 5 AM (early morning)
                    evening_events.append(event)
            else:
                daytime_events.append(event)
        elif "PM" in time_str:
            # Afternoon/Evening events
            hour_match = re.search(r'(\d{1,2}):', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                if hour >= 1 and hour <= 5:  # 1 PM to 5 PM
                    daytime_events.append(event)
                else:  # 6 PM to 12 PM (evening/night)
                    evening_events.append(event)
            else:
                evening_events.append(event)
        else:
            # If no AM/PM indicator, default to evening
            evening_events.append(event)

    # Create the new date section
    new_section = f"\n## {date_header}\n\n"

    # Add daytime events if any exist
    if daytime_events:
        new_section += "### Daytime Events\n\n"
        for event in daytime_events:
            new_section += format_single_event(event)

    # Add evening events if any exist
    if evening_events:
        if daytime_events:
            new_section += "\n"
        new_section += "### Evening Events\n\n"
        for event in evening_events:
            new_section += format_single_event(event)

    # Find the end of the document before the "Museums & Galleries" section
    museums_pattern = r"\n## Museums & Galleries"
    museums_match = re.search(museums_pattern, content)

    if museums_match:
        # Insert before the Museums section
        content = content[:museums_match.start()] + new_section + content[museums_match.start():]
    else:
        # Append to the end of the document
        content += new_section

    return content


def format_single_event(event: Dict) -> str:
    """
    Format a single event in markdown format following the existing structure.
    """
    # Clean up the title to remove any extra formatting
    clean_title = event['title'].replace('\n', ' ').strip()

    # Only include description if it's available and not generic
    description_line = ""
    if event.get('description') and event['description'] != "Description not available":
        description_line = f"  - Description: {event['description']}\n"

    return f"- **{clean_title}**\n\n  - Time: {event['time']}\n  - Location: {event['location']}\n{description_line}  - Link: {event['link']}\n\n"


def read_existing_events(file_path: str) -> str:
    """
    Read the existing events file.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def get_existing_links_from_file(file_path: str) -> set:
    """
    Extract all existing event links from the events.md file to avoid duplicates.
    """
    existing_links = set()
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find all links in the file
            links = re.findall(r'- Link: (https?://[^\s\n\r]+)', content)
            existing_links.update(links)
    return existing_links


async def scrape_meetup_events(location_code: str, search_terms: List[str] = None, filters: List[str] = None) -> List[Dict]:
    """
    Scrape events from Meetup based on location and search terms.
    """
    events = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=30000)
        page = await browser.new_page()

        try:
            base_url = f"https://www.meetup.com/find/?location={location_code}&source=EVENTS"

            if search_terms:
                search_param = "+".join(search_terms)
                base_url += f"&keywords={search_param}"

            if filters:
                for filter_type in filters:
                    if filter_type in ["this-weekend", "today", "tomorrow", "this-week"]:
                        base_url += f"&dateRange={filter_type}"
                        break

            print(f"Accessing Meetup URL: {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            await safe_wait(page, 5000)

            if hasattr(page, 'content'):  # For Playwright-based browsers
                content = await page.content()
            else:  # For pydoll Tab objects
                content = await page.execute_script("return document.documentElement.outerHTML;")
            soup = BeautifulSoup(content, 'html.parser')

            # Find event cards - look for divs with event links inside
            all_divs = soup.find_all('div')
            event_cards = []
            for div in all_divs:
                # Check if this div contains an event link
                event_link = div.find('a', href=re.compile(r'/events/\d+'))
                if event_link:
                    event_cards.append(div)

            print(f"Found {len(event_cards)} Meetup event cards")

            for i, card in enumerate(event_cards[:CONFIG["MAX_EVENTS_PER_PAGE"]]):
                try:
                    print(f"Processing Meetup event {i+1}/{min(len(event_cards), CONFIG['MAX_EVENTS_PER_PAGE'])}")

                    # Extract event title and link
                    link_elem = card.find('a', href=re.compile(r'/events/\d+'))
                    if not link_elem:
                        continue

                    title = link_elem.get_text(strip=True)
                    href = link_elem.get('href', '')
                    
                    if not title or len(title.strip()) < 3:
                        continue

                    # Clean title
                    title = title.strip()
                    title = re.sub(r'^\s*[-•·]\s*|\s*[-•·]\s*$', '', title)
                    
                    if not title:
                        continue

                    # Construct link
                    if href.startswith('/'):
                        link = "https://www.meetup.com" + href.split('?')[0]
                    else:
                        link = href.split('?')[0]

                    # Extract date and time from card text
                    card_text = card.get_text()
                    
                    # Parse date - look for "Month Day" pattern
                    month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})', card_text)
                    event_date = datetime.now().date()
                    
                    if month_match:
                        month_str = month_match.group(1)
                        day_str = month_match.group(2)
                        date_str = f"{month_str} {day_str}, {datetime.now().year}"
                        try:
                            event_date = parse_event_date(date_str)
                        except:
                            pass

                    # Parse time - look for "H:MMPM" or "HhMMAM" format
                    time_str = "TBA"
                    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)', card_text)
                    if time_match:
                        hour = time_match.group(1)
                        minute = time_match.group(2) or "00"
                        period = time_match.group(3).upper()
                        time_str = f"{hour}:{minute}{period}"
                    else:
                        # Try simpler format
                        time_match = re.search(r'(\d{1,2})\s*(AM|PM|am|pm)', card_text)
                        if time_match:
                            time_str = f"{time_match.group(1)}:00{time_match.group(2).upper()}"

                    location = "Location TBA"
                    is_free = True
                    description = "Description not available"

                    if link != "N/A":
                        try:
                            description = await scrape_meetup_event_description(page, link)
                        except Exception as e:
                            print(f"Could not fetch description: {e}")

                    event_info = {
                        'title': title,
                        'link': link,
                        'date': event_date,
                        'time': time_str,
                        'location': location,
                        'description': description
                    }
                    events.append(event_info)
                    print(f"Added Meetup event: {title[:50]}")

                except Exception as e:
                    print(f"Error processing Meetup event {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping Meetup events: {e}")

        finally:
            await browser.close()

    return events


async def scrape_meetup_event_description(page, event_link: str) -> str:
    """
    Scrape the description from a specific Meetup event page.
    """
    try:
        # Navigate to the event page
        await page.goto(event_link, wait_until="networkidle", timeout=15000)

        # Wait for content to load
        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
            await page.wait_for_timeout(3000)
        else:  # For pydoll Tab objects
            await asyncio.sleep(3.0)

        # Get page content
        if hasattr(page, 'content'):  # For Playwright-based browsers
            content = await page.content()
        else:  # For pydoll Tab objects
            result = await page.execute_script("return document.documentElement.outerHTML")
            # Handle potential dict response from pydoll
            if isinstance(result, dict) and 'result' in result:
                content = result['result']
            elif isinstance(result, dict) and 'value' in result:
                content = result['value']
            elif isinstance(result, str):
                content = result
            else:
                content = str(result) if result is not None else ""
        soup = BeautifulSoup(content, 'html.parser')

        # Look for description in various possible locations
        description = ""

        # Look for common description selectors
        desc_selectors = [
            'div[data-testid="event-details"]',
            'div[itemprop="description"]',
            '.event-description',
            '.event-details',
            '[data-automation="event-description"]'
        ]

        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                break

        # Clean up the description
        if description:
            # Remove extra whitespace and newlines
            description = re.sub(r'\s+', ' ', description)
            # Limit length to avoid overly long descriptions
            if len(description) > 300:
                description = description[:300] + "..."

        return description if description else "Description not available"

    except Exception as e:
        print(f"Error scraping Meetup description for {event_link}: {e}")
        return "Description not available"


async def scrape_luma_events(city: str) -> List[Dict]:
    """
    Scrape events from Luma calendar for a specific city.
    """
    events = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=30000)
        page = await browser.new_page()

        try:
            # Handle special city codes
            if city == "sf":
                city_url = "https://luma.com/sf"
            elif city == "nyc":
                city_url = "https://luma.com/nyc"
            elif city == "la":
                city_url = "https://luma.com/la"
            elif city == "dc":
                city_url = "https://luma.com/dc"
            else:
                # Convert city name to URL format (replace spaces with dashes)
                formatted_city = city.replace(" ", "-").replace("_", "-").lower()
                city_url = f"https://luma.com/{formatted_city}"

            print(f"Accessing Luma URL: {city_url}")
            await page.goto(city_url, wait_until="networkidle", timeout=30000)

            # Wait for content to load
            await safe_wait(page, 5000)

            # Get page content
            if hasattr(page, 'content'):  # For Playwright-based browsers
                content = await page.content()
            else:  # For pydoll Tab objects
                content = await page.execute_script("return document.documentElement.outerHTML;")
            soup = BeautifulSoup(content, 'html.parser')

            # Find event cards on Luma
            event_cards = soup.find_all('article', class_=re.compile(r'.*event.*', re.IGNORECASE))
            if not event_cards:
                event_cards = soup.find_all('div', class_=re.compile(r'.*event.*', re.IGNORECASE))

            print(f"Found {len(event_cards)} Luma event cards")

            for i, card in enumerate(event_cards[:CONFIG["MAX_EVENTS_PER_PAGE"]]):
                try:
                    print(f"Processing Luma event {i+1}/{min(len(event_cards), CONFIG['MAX_EVENTS_PER_PAGE'])}")

                    # Extract event title - try more specific selectors based on actual Luma structure
                    title_elem = None

                    # Look for headings inside event cards
                    title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if not title_elem:
                        # Look for links that are likely to contain the event title
                        # Look for links with event-related href patterns
                        link_elem = card.find('a', href=re.compile(r'/event/|/e/|event'))
                        if link_elem:
                            # Check if the link contains a heading
                            heading_in_link = link_elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if heading_in_link:
                                title_elem = heading_in_link
                            else:
                                # Use the link text itself if it's substantial
                                link_text = link_elem.get_text(strip=True)
                                if len(link_text) > 5:  # If it has substantial text, use it
                                    title_elem = link_elem
                    if not title_elem:
                        # Look for divs or spans that might contain the title
                        title_elem = card.find(['div', 'span'], class_=re.compile(r'.*title.*|.*headline.*|.*name.*|.*event.*', re.IGNORECASE))
                    if not title_elem:
                        # Look for any text that might be the event title
                        # Find the longest text element that doesn't look like a location
                        text_elements = card.find_all(['div', 'span', 'p'])
                        for elem in text_elements:
                            text = elem.get_text(strip=True)
                            # Skip if it looks like a location
                            if not re.search(r'Washington|DC|District of Columbia|Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Venue|Building|Place|Square|Court|Lane|Circle|Drive|Boulevard|Blvd', text, re.IGNORECASE):
                                if len(text) > 10 and not re.search(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', text, re.IGNORECASE):
                                    title_elem = elem
                                    break

                    if title_elem:
                        if title_elem.name == 'a':
                            # If it's a link, look for headings inside it first
                            title_tag = title_elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if title_tag:
                                title = title_tag.get_text(strip=True)
                            else:
                                title = title_elem.get_text(strip=True)
                        else:
                            title = title_elem.get_text(strip=True)

                        # Clean up the title
                        if title:
                            # Remove common UI elements from the title
                            title = re.sub(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?|Going fast|Save this event|Share this event', '', title, flags=re.IGNORECASE).strip()
                            # Remove leading/trailing punctuation
                            title = re.sub(r'^[-\s·]+|[-\s·]+$', '', title)
                            # Remove extra whitespace
                            title = re.sub(r'\s+', ' ', title)
                    else:
                        title = "Luma Event Title Unknown"

                    if not title or len(title.strip()) < 3:
                        continue

                    # Extract event link - look for the main event card link
                    link_elem = None
                    # First, look for the main card link (usually the whole event card is clickable)
                    link_elem = card.find('a', href=re.compile(r'/event/|/e/|event'))
                    if not link_elem:
                        # Look for any link that might be the event link
                        all_links = card.find_all('a', href=True)
                        for link_candidate in all_links:
                            href = link_candidate.get('href', '')
                            if '/event/' in href or '/e/' in href or 'event' in href.lower():
                                link_elem = link_candidate
                                break

                    if link_elem and link_elem.get('href'):
                        href = link_elem.get('href')
                        if href.startswith('/'):
                            link = "https://luma.com" + href
                        elif href.startswith('http'):
                            link = href
                        else:
                            link = "https://luma.com/" + href
                    else:
                        link = "N/A"

                    # Extract date and time - look for elements with date/time information
                    date_time_elem = None
                    # Look for elements containing date/time information
                    all_time_elements = card.find_all(['time', 'span', 'div', 'p'], string=re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Tomorrow|Today|This week|\d{1,2}:\d{2})', re.IGNORECASE))

                    for elem in all_time_elements:
                        text = elem.get_text(strip=True)
                        # Skip if this is an urgency signal like "Almost full", "Sales end soon", etc.
                        if not re.search(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', text, re.IGNORECASE):
                            date_time_elem = elem
                            break

                    if date_time_elem:
                        date_time_str = date_time_elem.get_text(strip=True)
                        print(f"Date/time string found: {date_time_str}")  # Debugging

                        # Extract date portion - more comprehensive regex
                        date_match = re.search(r'([A-Z][a-z]+,\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|[A-Z][a-z]+\s+\d{1,2}\s*-\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4})', date_time_str)
                        if date_match:
                            date_str = date_match.group(1)
                            event_date = parse_event_date(date_str)
                        else:
                            # Look for simpler date patterns
                            simple_date_match = re.search(r'([A-Z][a-z]+ \d{1,2})', date_time_str)
                            if simple_date_match:
                                # Add current year to the date
                                date_with_year = simple_date_match.group(1) + f", {datetime.now().year}"
                                event_date = parse_event_date(date_with_year)
                            else:
                                # Check for relative dates like "Tomorrow", "Today", "This week"
                                # Look for day followed by time (e.g., "Tomorrow • 6:00 PM")
                                day_time_match = re.search(r'(Tomorrow|Today|[A-Z][a-z]+)\s*•?\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}(?:AM|PM|am|pm))', date_time_str, re.IGNORECASE)
                                if day_time_match:
                                    day_part = day_time_match.group(1).lower()
                                    time_part = day_time_match.group(2)

                                    if "tomorrow" in day_part:
                                        event_date = (datetime.now() + timedelta(days=1)).date()
                                    elif "today" in day_part:
                                        event_date = datetime.now().date()
                                    else:
                                        # Try to find the next occurrence of this day
                                        target_day = day_part.capitalize()
                                        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                                        if target_day in days:
                                            target_idx = days.index(target_day)
                                            current_idx = datetime.now().weekday()
                                            days_ahead = target_idx - current_idx
                                            if days_ahead <= 0:  # Target day already happened this week
                                                days_ahead += 7
                                            event_date = (datetime.now() + timedelta(days_ahead)).date()
                                        else:
                                            event_date = datetime.now().date()

                                # If no day-time pattern, check for other patterns
                                elif "monday" in date_time_str.lower() or "tuesday" in date_time_str.lower() or \
                                     "wednesday" in date_time_str.lower() or "thursday" in date_time_str.lower() or \
                                     "friday" in date_time_str.lower() or "saturday" in date_time_str.lower() or \
                                     "sunday" in date_time_str.lower():
                                    # Try to find the next occurrence of this day
                                    day_name = [day for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] if day in date_time_str.lower()]
                                    if day_name:
                                        target_day = day_name[0].capitalize()
                                        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                                        target_idx = days.index(target_day)
                                        current_idx = datetime.now().weekday()
                                        days_ahead = target_idx - current_idx
                                        if days_ahead <= 0:  # Target day already happened this week
                                            days_ahead += 7
                                        event_date = (datetime.now() + timedelta(days_ahead)).date()
                                    else:
                                        event_date = datetime.now().date()
                                else:
                                    event_date = datetime.now().date()
                                time_str = "TBA"
                    else:
                        event_date = datetime.now().date()
                        time_str = "TBA"

                    # Extract location - look for elements containing location information
                    location_elem = None
                    # Look for elements that contain location-related keywords but not urgency signals
                    all_location_elements = card.find_all(['span', 'div', 'p'], string=re.compile(r'Washington|DC|District of Columbia|Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Venue|Building|Place|Square|Court|Lane|Circle|Drive|Boulevard|Blvd', re.IGNORECASE))

                    for elem in all_location_elements:
                        text = elem.get_text(strip=True)
                        # Skip if this is an urgency signal
                        if not re.search(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', text, re.IGNORECASE):
                            location_elem = elem
                            break

                    if location_elem:
                        location = location_elem.get_text(strip=True)
                        # Clean up location text
                        location = re.sub(r'^[-\s·]+|[-\s·]+$', '', location)
                        # Remove urgency signals that might have slipped through
                        location = re.sub(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', '', location, flags=re.IGNORECASE).strip()
                    else:
                        location = "Location TBA"

                    # For Luma, assume all events are free unless specified otherwise
                    is_free = True

                    # Scrape description if available
                    description = "Description not available"
                    if link != "N/A":
                        try:
                            description = await scrape_luma_event_description(page, link)
                        except:
                            pass

                    # Add event to list if it's free and not a duplicate
                    event_info = {
                        'title': title,
                        'link': link,
                        'date': event_date,
                        'time': time_str,
                        'location': location,
                        'description': description
                    }
                    events.append(event_info)
                    print(f"Added Luma event: {title[:50]}...")

                except Exception as e:
                    print(f"Error processing Luma event element {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping Luma events: {e}")

        finally:
            await browser.close()

    return events


async def scrape_luma_event_description(page, event_link: str) -> str:
    """
    Scrape the description from a specific Luma event page.
    """
    try:
        # Navigate to the event page
        await page.goto(event_link, wait_until="networkidle", timeout=15000)

        # Wait for content to load
        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
            await page.wait_for_timeout(3000)
        else:  # For pydoll Tab objects
            await asyncio.sleep(3.0)

        # Get page content
        if hasattr(page, 'content'):  # For Playwright-based browsers
            content = await page.content()
        else:  # For pydoll Tab objects
            result = await page.execute_script("return document.documentElement.outerHTML")
            # Handle potential dict response from pydoll
            if isinstance(result, dict) and 'result' in result:
                content = result['result']
            elif isinstance(result, dict) and 'value' in result:
                content = result['value']
            elif isinstance(result, str):
                content = result
            else:
                content = str(result) if result is not None else ""
        soup = BeautifulSoup(content, 'html.parser')

        # Look for description in various possible locations
        description = ""

        # Look for common description selectors
        desc_selectors = [
            'div[data-testid="event-description"]',
            'div[itemprop="description"]',
            '.event-description',
            '.event-details',
            '[data-automation="event-description"]'
        ]

        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                break

        # Clean up the description
        if description:
            # Remove extra whitespace and newlines
            description = re.sub(r'\s+', ' ', description)
            # Limit length to avoid overly long descriptions
            if len(description) > 300:
                description = description[:300] + "..."

        return description if description else "Description not available"

    except Exception as e:
        print(f"Error scraping Luma description for {event_link}: {e}")
        return "Description not available"


# Configuration for API services (add after imports)
ABROWSERBSE_API_KEY = os.environ.get("BROWSERBASE_API_KEY")
ANCHOR_BROWSER_API_KEY = os.environ.get("ANCHOR_BROWSER_API_KEY")


async def scrape_with_browserbase(url: str, selector: str = None) -> Optional[str]:
    """
    Fallback method to scrape a page using Browserbase API.
    Returns HTML content of the page.
    
    Requires BROWSERBASE_API_KEY environment variable.
    Browserbase: https://browserbase.com/docs
    """
    if not BROWSERBASE_API_KEY:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {BROWSERBASE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "url": url,
                "timeout": 30000,
                "perform_actions": [{"type": "scroll", "direction": "down", "amount": 3}]
            }
            
            async with session.post(
                "https://api.browserbase.com/v1/screenshot",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("html")
                    
    except Exception as e:
        print(f"Browserbase scraping failed: {e}")
    
    return None


async def scrape_with_anchor_browser(url: str) -> Optional[str]:
    """
    Fallback method to scrape a page using Anchor Browser API.
    Returns HTML content of the page.
    
    Requires ANCHOR_BROWSER_API_KEY environment variable.
    Anchor Browser: https://www.anchorbrowser.io/docs
    """
    if not ANCHOR_BROWSER_API_KEY:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {ANCHOR_BROWSER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "url": url,
                "wait": "networkidle",
                "timeout": 30
            }
            
            async with session.post(
                "https://api.anchorbrowser.io/v1/page",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("content")
                    
    except Exception as e:
        print(f"Anchor Browser scraping failed: {e}")
    
    return None


async def scrape_with_api_fallback(url: str, fallback_order: List[str] = None) -> Optional[str]:
    """
    Try to scrape a URL using multiple API fallback methods in order.
    
    Args:
        url: The URL to scrape
        fallback_order: List of API names to try in order 
                       (default: ["browserbase", "anchor_browser"])
    
    Returns:
        HTML content if successful, None otherwise
    """
    if fallback_order is None:
        fallback_order = ["browserbase", "anchor_browser"]
    
    for api_name in fallback_order:
        print(f"Trying {api_name} API for {url}...")
        
        if api_name == "browserbase":
            content = await scrape_with_browserbase(url)
        elif api_name == "anchor_browser":
            content = await scrape_with_anchor_browser(url)
        else:
            continue
        
        if content:
            print(f"Successfully scraped with {api_name}")
            return content
    
    return None


async def main():
    """
    Main function to scrape events from various sources and update events.md
    """
    print("Starting events scraper...")

    # Read existing content first
    file_path = os.path.join(os.path.dirname(__file__), "events.md")
    existing_content = read_existing_events(file_path)

    # Get existing links to avoid duplicates
    existing_links = get_existing_links_from_file(file_path)
    print(f"Found {len(existing_links)} existing event links to avoid")

    all_events = []

    # Scrape from Eventbrite (always enabled)
    print("Scraping from Eventbrite...")
    urls = get_eventbrite_urls()

    # Scrape each URL
    for url in urls:
        print(f"Scraping: {url}")
        events = await scrape_eventbrite_page(url, existing_links)
        all_events.extend(events)
        print(f"Found {len(events)} new events on this page")

    # Check if we should scrape from Meetup
    if CONFIG["MODES"]["ENABLE_MEETUP_SCRAPING"]:
        print("Scraping from Meetup...")
        # Convert location to Meetup format (e.g., dc--washington -> us--dc--washington)
        parts = CONFIG["LOCATION"].split("--")
        if len(parts) >= 2:
            state = parts[0]
            city_parts = parts[1:]
            city = "-".join(city_parts)
            meetup_location = f"us--{state}--{city}"
        else:
            meetup_location = CONFIG["LOCATION"]  # Use as-is if format is unexpected

        search_terms = CONFIG["MODES"]["CUSTOM_SEARCH_TERMS"] if CONFIG["MODES"]["CUSTOM_SEARCH_TERMS"] else []
        filters = CONFIG["FILTERS_TO_USE"] if CONFIG["FILTERS_TO_USE"] else []

        meetup_events = await scrape_meetup_events(meetup_location, search_terms, filters)
        all_events.extend(meetup_events)
        print(f"Found {len(meetup_events)} new Meetup events")

    # Check if we should scrape from Luma
    if CONFIG["MODES"]["ENABLE_LUMA_SCRAPING"]:
        print("Scraping from Luma...")
        # Convert location to Luma format
        luma_city = CONFIG["LOCATION"].replace("--", "-").replace(" ", "-").lower()
        # Handle special cases
        if luma_city == "dc-washington":
            luma_city = "dc"
        elif luma_city == "ny-new-york":
            luma_city = "nyc"
        elif luma_city == "ca-los-angeles":
            luma_city = "la"
        elif luma_city == "ca-san-francisco":
            luma_city = "sf"

        luma_events = await scrape_luma_events(luma_city)
        all_events.extend(luma_events)
        print(f"Found {len(luma_events)} new Luma events")

    print(f"Total new events found: {len(all_events)}")

    if all_events:
        # Format events for markdown, passing existing content to preserve structure
        updated_content = format_events_for_markdown(all_events, existing_content)

        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        print(f"Successfully added {len(all_events)} new events to {file_path}")
    else:
        print("No new events found.")

    print("Scraping completed.")


if __name__ == "__main__":
    asyncio.run(main())