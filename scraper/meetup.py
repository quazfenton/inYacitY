#!/usr/bin/env python3
"""
Fixed Meetup scraper - Scrapes event details from individual event pages
"""

import asyncio
import json
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from simple_browser import create_browser, close_browser


async def scrape_meetup_event_detail(page, event_url: str) -> dict:
    """
    Navigate to Meetup event page and scrape full details including description and location.
    """
    try:
        await page.goto(event_url, wait_until="domcontentloaded", timeout=15000)
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

        # Extract description
        description = "Description not available"

        # Try the p.mb-ds2-10 selector
        desc_elem = soup.select_one('p.mb-ds2-10')
        if desc_elem:
            desc = desc_elem.get_text(strip=True)
            if len(desc) > 20:
                # Clean up description by removing unwanted Unicode characters
                cleaned_desc = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', desc)  # Common Unicode punctuation/spaces
                cleaned_desc = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', cleaned_desc)  # Specific quotes, dashes, ellipsis
                cleaned_desc = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', cleaned_desc)  # Non-breaking spaces and zero-width chars
                cleaned_desc = re.sub(r'[\ud800-\udfff]', ' ', cleaned_desc)  # Remove surrogate pairs (emojis and other symbols)
                cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc)  # Normalize whitespace
                description = cleaned_desc[:500].strip()

        # Try other selectors as fallback
        if description == "Description not available":
            for selector in ['div[data-testid="event-description"]', 'div[itemprop="description"]']:
                try:
                    elem = soup.select_one(selector)
                    if elem:
                        desc = elem.get_text(strip=True)
                        if len(desc) > 20:
                            # Clean up description by removing unwanted Unicode characters
                            cleaned_desc = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', desc)  # Common Unicode punctuation/spaces
                            cleaned_desc = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', cleaned_desc)  # Specific quotes, dashes, ellipsis
                            cleaned_desc = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', cleaned_desc)  # Non-breaking spaces and zero-width chars
                            cleaned_desc = re.sub(r'[\ud800-\udfff]', ' ', cleaned_desc)  # Remove surrogate pairs (emojis and other symbols)
                            cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc)  # Normalize whitespace
                            description = cleaned_desc[:500].strip()
                            break
                except:
                    pass

        # Extract location from event page
        location = "Location TBA"

        # Look for location in the specific format mentioned: <p class="ds2-r16 text-ds2-text-fill-tertiary-enabled">72 Spring St · New York, NY</p>
        location_elem = soup.select_one('p.ds2-r16.text-ds2-text-fill-tertiary-enabled')
        if location_elem:
            location_text = location_elem.get_text(strip=True)

            # Look for venue name in the preceding element with class ds2-k16 text-ds2-text-fill-primary-enabled
            venue_elem = location_elem.find_previous_sibling('p', class_='ds2-k16.text-ds2-text-fill-primary-enabled')
            if not venue_elem:
                # Try to find it as a general sibling
                for prev_elem in location_elem.find_all_previous('p'):
                    if 'ds2-k16' in prev_elem.get('class', []) and 'text-ds2-text-fill-primary-enabled' in prev_elem.get('class', []):
                        venue_elem = prev_elem
                        break

            if venue_elem:
                venue_name = venue_elem.get_text(strip=True)
                # Combine venue name with location
                location = f"{venue_name} - {location_text}" if location_text else venue_name
            elif location_text and len(location_text) > 5:  # Make sure it's a valid location
                # Just use the location text if no venue name found
                location = location_text

        # Clean up location by removing unwanted Unicode characters
        if location != "Location TBA":
            # More comprehensive Unicode character removal
            location = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', location)  # Common Unicode punctuation/spaces
            location = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', location)  # Specific quotes, dashes, ellipsis
            location = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', location)  # Non-breaking spaces and zero-width chars
            location = re.sub(r'\s+', ' ', location)  # Normalize whitespace
            location = location.strip()

        # Extract date and time from event page
        date_str = "2026-01-16"
        time_str = "TBA"

        # Look for date/time in event details
        all_text = soup.get_text()

        # Try to find date pattern
        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})', all_text)
        if date_match:
            month_str = date_match.group(1)
            day_str = date_match.group(2)
            if len(month_str) == 3:
                month_names = {'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April', 'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August', 'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'}
                month_str = month_names.get(month_str, month_str)

            try:
                parsed_date = datetime.strptime(f"{month_str} {day_str}, 2026", "%B %d, %Y")
                date_str = parsed_date.strftime("%Y-%m-%d")
            except:
                pass

        # Try to find time
        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', all_text)
        if time_match:
            time_str = time_match.group(0)

        return {
            'description': description,
            'date': date_str,
            'time': time_str,
            'location': location
        }

    except Exception as e:
        print(f"     Error scraping event detail: {e}")
        return {
            'description': "Description not available",
            'date': "2026-01-16",
            'time': "TBA",
            'location': "Location TBA"
        }


def clean_meetup_title(title: str) -> str:
    """
    Clean Meetup title by removing emojis, dates, times, attendee counts, and 'by [group]' text.
    """
    if not title:
        return "Unknown Event"

    # Remove emojis and icon text
    title = re.sub(r'[\u200b\u200c\u200d\ufeff\ud83d-\udfff\ude00-\ude4f\ude80-\udeff]', ' ', title)
    title = re.sub(r'icon', '', title, flags=re.IGNORECASE)

    # Remove date patterns like "Mon, Jan 19 · 6:15 PM EST"
    title = re.sub(r'[A-Z][a-z]{2}, [A-Z][a-z]{2,3} \d{1,2} · \d{1,2}:\d{2} [AP]M [A-Z]{2,3}', '', title)
    title = re.sub(r'[A-Z][a-z]{2}, [A-Z][a-z]{2,3} \d{1,2} ·', '', title)
    title = re.sub(r'Sat, Jan \d{1,2} ·', '', title)

    # Remove attendee count
    title = re.sub(r'\d+\.?\d*\s*attendees?', '', title, flags=re.IGNORECASE)

    # Remove "by [group]" text
    title = re.sub(r'\s*by\s+[^•\n]+', '', title, flags=re.IGNORECASE)

    # Clean up extra whitespace and punctuation
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'^[\s•\-]+|[\s•\-]+$', '', title)
    # Clean up Unicode characters more comprehensively
    title = re.sub(r'[\u0080-\u009f\u2000-\u206f\u2e00-\u2e7f]', ' ', title)  # Common Unicode punctuation/spaces
    title = re.sub(r'[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2010-\u2015]', ' ', title)  # Specific quotes, dashes, ellipsis
    title = re.sub(r'[\u00a0\ufeff\u200b\u200c\u200d]', ' ', title)  # Non-breaking spaces and zero-width chars
    title = re.sub(r'[\ud800-\udfff]', ' ', title)  # Remove surrogate pairs (emojis and other symbols)
    title = re.sub(r'\s+', ' ', title)  # Normalize whitespace

    return title.strip()


async def scrape_meetup(location_code: str, output_file: str = "meetup_events.json", search_terms=None, filters=None):
    """
    Scrape Meetup events for a location.
    """
    if search_terms is None:
        search_terms = []
    if filters is None:
        filters = []
    
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
    found_links = set()
    
    browser = None
    
    try:
        # Create simple browser
        browser, page = await create_browser(headless=True)
        
        print(f"🌐 Using simple browser")
        
        try:
            base_url = f"https://www.meetup.com/find/?location={location_code}&source=EVENTS"

            if search_terms:
                search_param = "+".join(search_terms)
                base_url += f"&keywords={search_param}"

            if filters:
                for filter_type in filters:
                    if filter_type in ["this-weekend", "today", "tomorrow", "this-weekend", "this-week"]:
                        base_url += f"&dateRange={filter_type}"
                        break

            url = base_url
            print(f"Scraping: {url}")

            # Simple navigation
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Scroll down to load more events
            for scroll_count in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                await page.wait_for_timeout(2000)

                # Check if there's a "Load more" button
                try:
                    load_more_button = await page.query_selector('button:has-text("Load more")')
                    if load_more_button:
                        await load_more_button.click()
                        await page.wait_for_timeout(3000)
                except:
                    pass

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Find all event links (href contains /events/)
            event_links = soup.find_all('a', href=re.compile(r'/events/'))
            print(f"Found {len(event_links)} potential event links on initial page")

            # Process events from the initial page
            for i, link_elem in enumerate(event_links):
                try:
                    href = link_elem.get('href', '')
                    if not href or '/events/' not in href:
                        continue

                    # Extract clean URL (remove query params)
                    event_url = f"https://www.meetup.com{href.split('?')[0]}" if href.startswith('/') else href.split('?')[0]

                    # Skip if we've already processed this link in this run
                    if event_url in found_links:
                        continue
                    found_links.add(event_url)

                    # Get title from link text
                    raw_title = link_elem.get_text(strip=True)
                    title = clean_meetup_title(raw_title)

                    # Skip if title is too short after cleaning
                    if not title or len(title) < 3:
                        continue

                    # Skip if already scraped
                    if event_url in existing_events:
                        print(f"  ⊘ Skipping (already scraped): {title[:50]}")
                        continue

                    # Scrape event detail page
                    print(f"  → Fetching details: {title[:50]}")
                    detail = await scrape_meetup_event_detail(page, event_url)

                    event_info = {
                        'title': title,
                        'date': detail['date'],
                        'time': detail['time'],
                        'link': event_url,
                        'description': detail['description'],
                        'location': detail['location'],
                        'source': 'Meetup',
                        'city': location_code
                    }

                    new_events.append(event_info)
                    print(f"  ✓ {title[:50]:<50} | {detail['date']} {detail['time']}")

                except Exception as e:
                    print(f"  Error parsing event link: {e}")
                    continue

            # Try to navigate to additional pages if pagination exists
            page_num = 2
            max_pages = 5  # Limit to prevent infinite loops
            while page_num <= max_pages:
                try:
                    # Construct the URL for the next page
                    next_page_url = f"{base_url}&page={page_num}"
                    print(f"Scraping additional page: {next_page_url}")

                    await page.goto(next_page_url, wait_until="domcontentloaded", timeout=30000)
                    if hasattr(page, 'wait_for_timeout'):
                        await page.wait_for_timeout(3000)
                    else:
                        await asyncio.sleep(3.0)

                    # Scroll to load more events on this page
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                        await page.wait_for_timeout(2000)
                    else:  # For pydoll Tab objects
                        await asyncio.sleep(2.0)

                    # Get page content - handle both Playwright and pydoll
                    if hasattr(page, 'content'):
                        content = await page.content()
                    else:
                        result = await page.execute_script("return document.documentElement.outerHTML")
                        if isinstance(result, dict) and 'result' in result:
                            content = result['result']
                        elif isinstance(result, dict) and 'value' in result:
                            content = result['value']
                        elif isinstance(result, str):
                            content = result
                        else:
                            content = str(result) if result is not None else ""
                    
                    soup = BeautifulSoup(content, 'html.parser')

                    # Find event links on this page
                    page_event_links = soup.find_all('a', href=re.compile(r'/events/'))
                    print(f"Found {len(page_event_links)} potential event links on page {page_num}")

                    if not page_event_links:  # If no more events found, break
                        break

                    # Process events from this page
                    for link_elem in page_event_links:
                        try:
                            href = link_elem.get('href', '')
                            if not href or '/events/' not in href:
                                continue

                            # Extract clean URL (remove query params)
                            event_url = f"https://www.meetup.com{href.split('?')[0]}" if href.startswith('/') else href.split('?')[0]

                            # Skip if we've already processed this link in this run
                            if event_url in found_links:
                                continue
                            found_links.add(event_url)

                            # Get title from link text
                            raw_title = link_elem.get_text(strip=True)
                            title = clean_meetup_title(raw_title)

                            # Skip if title is too short after cleaning
                            if not title or len(title) < 3:
                                continue

                            # Skip if already scraped
                            if event_url in existing_events:
                                print(f"  ⊘ Skipping (already scraped): {title[:50]}")
                                continue

                            # Scrape event detail page
                            print(f"  → Fetching details: {title[:50]}")
                            detail = await scrape_meetup_event_detail(page, event_url)

                            event_info = {
                                'title': title,
                                'date': detail['date'],
                                'time': detail['time'],
                                'link': event_url,
                                'description': detail['description'],
                                'location': detail['location'],
                                'source': 'Meetup',
                                'city': location_code
                            }

                            new_events.append(event_info)
                            print(f"  ✓ {title[:50]:<50} | {detail['date']} {detail['time']}")

                        except Exception as e:
                            print(f"  Error parsing event link on page {page_num}: {e}")
                            continue

                    page_num += 1

                except Exception as e:
                    print(f"Error navigating to page {page_num}: {e}")
                    break

            print(f"\nFound {len(new_events)} new events")
        
        except Exception as e:
            print(f"Error during scraping: {e}")
            
    except Exception as e:
        print(f"Error accessing Meetup: {e}")
    
    finally:
        if browser:
            await close_browser(browser)
    
    # Merge with existing and save
    all_events = list(existing_events.values()) + new_events
    
    with open(output_file, 'w') as f:
        json.dump({'events': all_events, 'total': len(all_events)}, f, indent=2)
    
    print(f"Saved {len(all_events)} total events to {output_file}")
    
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

    # Convert location format for meetup (e.g., dc--washington -> us--dc--washington)
    if '--' in location:
        parts = location.split('--')
        if len(parts) >= 2:
            meetup_location = f"us--{parts[0]}--{parts[1]}"
        else:
            meetup_location = location
    else:
        meetup_location = f"us--{location}"

    await scrape_meetup(meetup_location, 'meetup_events.json', [], [])


if __name__ == '__main__':
    asyncio.run(main())
