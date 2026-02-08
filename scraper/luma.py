#!/usr/bin/env python3
"""
Fixed Luma scraper - Correctly finds event cards and scrapes descriptions from detail pages
"""

import asyncio
import json
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from simple_browser import create_browser, close_browser


async def scrape_luma_event_description(page, event_url: str) -> str:
    """
    Scrape description from individual Luma event page.
    """
    try:
        # Navigate to event page
        full_url = f"https://www.luma.com/{event_url}"
        await page.goto(full_url, wait_until="domcontentloaded", timeout=15000)
        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
            await page.wait_for_timeout(2000)
        else:  # For pydoll Tab objects
            await asyncio.sleep(2.0)

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

        # Look for description in common places
        desc_selectors = [
            ('div[class*="description"]', None),
            ('div[class*="about"]', None),
            ('p', lambda t: len(t) > 50),  # First substantial paragraph
            ('div', lambda t: 'description' in t or 'about' in t.lower() if isinstance(t, str) else False),
        ]

        for selector, check in desc_selectors:
            if '[' in selector:  # CSS selector
                elem = soup.select_one(selector)
                if elem:
                    desc = elem.get_text(strip=True)
                    if len(desc) > 20:
                        # Clean up the description by removing unwanted prefixes
                        cleaned_desc = re.sub(r'^About Event\s*', '', desc, flags=re.IGNORECASE)
                        cleaned_desc = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', cleaned_desc)  # Common Unicode punctuation/spaces
                        cleaned_desc = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', cleaned_desc)  # Specific quotes, dashes, ellipsis
                        cleaned_desc = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', cleaned_desc)  # Non-breaking spaces and zero-width chars
                        cleaned_desc = re.sub(r'[\ud800-\udfff]', ' ', cleaned_desc)  # Remove surrogate pairs (emojis and other symbols)
                        cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc)  # Normalize whitespace
                        return cleaned_desc[:250].strip()
            else:  # Tag selector
                for elem in soup.find_all(selector):
                    text = elem.get_text(strip=True)
                    if check is None or check(text):
                        if len(text) > 50:
                            # Clean up the description by removing unwanted prefixes
                            cleaned_text = re.sub(r'^About Event\s*', '', text, flags=re.IGNORECASE)
                            cleaned_text = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', cleaned_text)  # Common Unicode punctuation/spaces
                            cleaned_text = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', cleaned_text)  # Specific quotes, dashes, ellipsis
                            cleaned_text = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', cleaned_text)  # Non-breaking spaces and zero-width chars
                            cleaned_text = re.sub(r'[\ud800-\udfff]', ' ', cleaned_text)  # Remove surrogate pairs (emojis and other symbols)
                            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
                            return cleaned_text[:250].strip()

        return "Description not available"

    except Exception as e:
        print(f"     Error scraping description: {e}")
        return "Description not available"


async def scrape_luma(city: str, output_file: str = "luma_events.json"):
    """
    Scrape Luma events for a city.
    """

    # Handle special city codes (similar to scrapeevents.py)
    if city == "sf":
        city_url = "https://www.luma.com/sf"
    elif city == "nyc":
        city_url = "https://www.luma.com/nyc"
    elif city == "la":
        city_url = "https://www.luma.com/la"
    elif city == "dc":
        city_url = "https://www.luma.com/dc"
    else:
        # Convert city name to URL format (replace spaces with dashes)
        formatted_city = city.replace(" ", "-").replace("_", "-").lower()
        city_url = f"https://www.luma.com/{formatted_city}"

    # Load existing events to avoid duplicates
    existing_events = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                for event in data.get('events', []):
                    existing_events[event['link']] = event
            print(f"Loaded {len(existing_events)} existing events from {output_file}")
        except:
            pass

    new_events = []

    browser = None
    
    try:
        # Create simple browser
        browser, page = await create_browser(headless=True)
        
        print(f"🌐 Using simple browser")

        try:
            print(f"Scraping: {city_url}")
            
            # Simple navigation
            await page.goto(city_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            
            soup = BeautifulSoup(content, 'html.parser')

            # Find all date headers
            date_headers = soup.find_all('div', class_='date-title')
            print(f"Found {len(date_headers)} date headers")

            # Process each date group
            for date_header in date_headers:
                date_elem = date_header.find('div', class_='date')
                weekday_elem = date_header.find('div', class_='weekday')

                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    weekday = weekday_elem.get_text(strip=True) if weekday_elem else ""

                    # Parse the date
                    month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_text)
                    day_match = re.search(r'(\d{1,2})', date_text)

                    if month_match and day_match:
                        month_str = month_match.group(1)
                        day_str = day_match.group(1)
                        month_names = {'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April', 'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August', 'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'}
                        month_full = month_names.get(month_str, month_str)

                        try:
                            current_date = datetime.strptime(f"{month_full} {day_str}, 2026", "%B %d, %Y")
                            current_date_str = current_date.strftime("%Y-%m-%d")
                        except:
                            current_date_str = "2026-01-16"
                    else:
                        current_date_str = "2026-01-16"

                    # Find all event cards that follow this date header
                    # Get all divs and track indices properly
                    all_divs = list(soup.find_all('div'))
                    
                    # Find position of current date header by comparing elements
                    date_header_index = -1
                    for idx, div in enumerate(all_divs):
                        if div is date_header:
                            date_header_index = idx
                            break
                    
                    if date_header_index == -1:
                        continue

                    # Find position of next date header if it exists
                    next_date_header_index = -1
                    for idx in range(date_header_index + 1, len(all_divs)):
                        div = all_divs[idx]
                        if div.get('class') and 'date-title' in div.get('class', []):
                            next_date_header_index = idx
                            break

                    # Process all content-card divs between these positions
                    start_idx = date_header_index + 1
                    end_idx = next_date_header_index if next_date_header_index != -1 else len(all_divs)

                    for i in range(start_idx, end_idx):
                        div = all_divs[i]
                        if div.get('class') and 'content-card' in div.get('class', []):
                            # Extract event details from card
                            event_link_elem = div.find('a', href=re.compile(r'/[a-z0-9]+$'))
                            if not event_link_elem:
                                event_link_elem = div.find('a', href=re.compile(r'/[a-z0-9]+\?'))

                            if event_link_elem:
                                event_id = event_link_elem.get('href', '').strip('/')
                                if not event_id or '?' in event_id:
                                    event_id = event_id.split('?')[0]

                                if not event_id or len(event_id) < 8:
                                    continue

                                event_url = f"https://www.luma.com/{event_id}"

                                if event_url in existing_events:
                                    title = existing_events[event_url].get('title', 'Unknown')
                                    print(f"  ⊘ Skipping (already scraped): {title[:50]}")
                                    continue

                                # Extract title from h3
                                h3 = div.find('h3')
                                title = h3.get_text(strip=True) if h3 else "Unknown Event"
                                # Clean up title by removing unwanted Unicode characters and formatting
                                title = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', title)  # Common Unicode punctuation/spaces
                                title = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', title)  # Specific quotes, dashes, ellipsis
                                title = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', title)  # Non-breaking spaces and zero-width chars
                                title = re.sub(r'[\ud800-\udfff]', ' ', title)  # Remove surrogate pairs (emojis and other symbols)
                                title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                                title = title.strip()

                                # Extract time from card
                                card_text = div.get_text()
                                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', card_text)
                                time_str = time_match.group(0) if time_match else "TBA"

                                # Extract location (often in the card)
                                location = "Location TBA"

                                # Look for location in elements with the specific structure described
                                # Find the div with location icon (SVG with path for location marker) and text-ellipses class
                                location_elements = div.find_all('div', class_=re.compile(r'text-ellipses'))
                                for loc_elem in location_elements:
                                    # Check if this element is inside a container that has location-related attributes
                                    parent_container = loc_elem.find_parent('div', class_=re.compile(r'attribute|location|place|address', re.I))
                                    if parent_container:
                                        # Check if the parent has a location-related icon (SVG with location path)
                                        location_icon = parent_container.find('svg')
                                        if location_icon:
                                            # Check if the SVG has the specific path for location markers
                                            location_paths = location_icon.find_all('path')
                                            has_location_icon = any(
                                                'M2 6.854' in path.get('d', '') or 'M9.5 6.5' in path.get('d', '')
                                                for path in location_paths
                                            )

                                            if has_location_icon:
                                                location_text = loc_elem.get_text(strip=True)
                                                if location_text and not re.search(r'(?i)^by\s+', location_text):
                                                    location = location_text[:100]
                                                    break

                                # If still no location found, fall back to previous methods
                                if location == "Location TBA":
                                    # First, try to find location in the card text using common venue patterns
                                    location_patterns = [r'Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Blvd|Boulevard|Ln|Lane|Ct|Court|Pkwy|Parkway|Dr|Drive|Way|Place']
                                    location_match = re.search(r'([A-Za-z0-9\s,\.]+?(?:Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Blvd|Boulevard|Ln|Lane|Ct|Court|Pkwy|Parkway|Dr|Drive|Way|Place)[A-Za-z0-9\s,\.]*?)', card_text)
                                    if location_match:
                                        location = location_match.group(1).strip()[:100]
                                    else:
                                        # Look for venue names in the card (text that appears to be venues)
                                        # Check for text elements that might contain venue names
                                        venue_elements = div.find_all(['div', 'span'], class_=re.compile(r'venue|location|place|address', re.I))
                                        for elem in venue_elements:
                                            elem_text = elem.get_text(strip=True)
                                            if elem_text and len(elem_text) > 3 and not re.match(r'^\d+:\d+', elem_text):  # Not a time
                                                # Skip if it looks like a category or other non-location text
                                                if not re.search(r'(?i)(music|event|ticket|free|sold|out|buy|show|dj|live)', elem_text):
                                                    # Also skip if it looks like a person's name (contains "By" followed by names)
                                                    if not re.search(r'(?i)^by\s+[A-Z][a-z]+\s+[A-Z][a-z]+', elem_text):
                                                        location = elem_text[:100]
                                                        break

                                # Scrape event detail page for description
                                print(f"  → Fetching description from: {event_id}")
                                description = await scrape_luma_event_description(page, event_id)

                                event_info = {
                                    'title': title,
                                    'date': current_date_str,
                                    'time': time_str,
                                    'location': location,
                                    'link': event_url,
                                    'description': description,
                                    'source': 'Luma'
                                }

                                new_events.append(event_info)
                                print(f"  ✓ {title[:50]:<50} | {current_date_str} {time_str}")

            print(f"\nFound {len(new_events)} new events")

        except Exception as e:
            print(f"Error during scraping: {e}")

    except Exception as e:
        print(f"Error accessing Luma: {e}")

    finally:
        if browser:
            await close_browser(browser)

    # Merge with existing and save
    all_events = list(existing_events.values()) + new_events

    with open(output_file, 'w') as f:
        json.dump({'events': all_events, 'total': len(all_events)}, f, indent=2)

    print(f"Saved {len(all_events)} total events to {output_file}")

    return new_events

    return new_events


async def main():
    import json
    import os

    # Load configuration
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except:
            print("Warning: Could not load config.json, using defaults")

    # Get location from config, default to dc--washington if not specified
    location = config.get('LOCATION', 'dc--washington')

    # Map common location codes to luma cities
    location_to_luma = {
        'dc--washington': 'dc',
        'ny--new-york': 'nyc',
        'ca--los-angeles': 'la',
        'ca--san-francisco': 'sf',
        'tx--houston': 'houston',
        'il--chicago': 'chicago',
        'fl--miami': 'miami',
        'ma--boston': 'boston',
        'wa--seattle': 'seattle',
        'co--denver': 'denver',
        'ga--atlanta': 'atlanta',
        'nv--las-vegas': 'las-vegas',
        'mi--detroit': 'detroit',
        'or--portland': 'portland',
        'nc--charlotte': 'charlotte',
        'tn--nashville': 'nashville',
        'la--new-orleans': 'new-orleans',
        'fl--orlando': 'orlando',
        'fl--tampa': 'tampa',
        'ca--san-jose': 'san-jose',
        'tx--dallas': 'dallas',
        'tx--austin': 'austin',
        'va--richmond': 'richmond',
        'mn--minneapolis': 'minneapolis',
        'wi--milwaukee': 'milwaukee',
        'ky--louisville': 'louisville',
        'sc--charleston': 'charleston',
        'al--birmingham': 'birmingham',
        'ut--salt-lake-city': 'salt-lake-city',
        'nm--albuquerque': 'albuquerque'
    }

    luma_city = location_to_luma.get(location, 'houston')  # Default to houston if not found

    await scrape_luma(luma_city, 'luma_events.json')


if __name__ == '__main__':
    asyncio.run(main())