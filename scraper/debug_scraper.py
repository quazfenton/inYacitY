#!/usr/bin/env python3
"""
Debug script to scrape events from Eventbrite, Meetup, and Luma for Washington DC
"""

import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import os
from typing import Dict, List


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


async def scrape_meetup_events(location_code: str, search_terms: List[str] = None, filters: List[str] = None) -> List[Dict]:
    """
    Scrape events from Meetup based on location and search terms.
    """
    events = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, timeout=30000)  # Changed from True to False to avoid detection
        page = await browser.new_page()
        
        try:
            # Construct the meetup URL based on location and search terms
            # Meetup expects location in format like "us--dc--washington"
            base_url = f"https://www.meetup.com/find/?location={location_code}&source=EVENTS"

            if search_terms:
                # Add search terms to the URL
                search_param = "+".join(search_terms)
                base_url += f"&keywords={search_param}"

            if filters:
                # Add date filters to the URL
                for filter_type in filters:
                    if filter_type in ["this-weekend", "today", "tomorrow", "this-week"]:
                        base_url += f"&dateRange={filter_type}"
                        break  # Only add one date filter
            
            print(f"Accessing Meetup URL: {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            
            # Wait for content to load
            if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                await page.wait_for_timeout(5000)
            else:  # For pydoll Tab objects
                await asyncio.sleep(5.0)
            
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
            
            # Find event cards on Meetup
            event_cards = soup.find_all('div', {'data-testid': 'event-card'})
            if not event_cards:
                event_cards = soup.find_all('div', class_=re.compile(r'.*eventCard.*', re.IGNORECASE))
            
            print(f"Found {len(event_cards)} Meetup event cards")
            
            for i, card in enumerate(event_cards[:30]):  # Limit to first 30 events
                try:
                    print(f"Processing Meetup event {i+1}/{min(len(event_cards), 30)}")
                    
                    # Extract event title
                    title_elem = card.find('a', class_=re.compile(r'.*eventCardHeadline.*', re.IGNORECASE))
                    if not title_elem:
                        title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if not title_elem:
                        title_elem = card.find('div', class_=re.compile(r'.*headline.*', re.IGNORECASE))
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        # Clean up title
                        title = re.sub(r'Almost full|Sales end soon|Going fast|Save|Share|Follow|Attend|Buy|Tickets?', '', title, flags=re.IGNORECASE).strip()
                        title = re.sub(r'^[-\s·]+|[-\s·]+$', '', title)
                    else:
                        title = "Meetup Event Title Unknown"
                    
                    if not title or len(title.strip()) < 3:
                        continue
                    
                    # Extract event link
                    link_elem = card.find('a', href=re.compile(r'/events/'))
                    if link_elem and link_elem.get('href'):
                        href = link_elem.get('href')
                        if href.startswith('/'):
                            link = "https://www.meetup.com" + href
                        else:
                            link = href
                    else:
                        link = "N/A"
                    
                    # Extract date and time
                    date_elem = card.find('span', string=re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', re.IGNORECASE))
                    if date_elem:
                        date_time_str = date_elem.get_text(strip=True)
                        # Extract date portion
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
                                # Check for relative dates
                                if "tomorrow" in date_time_str.lower():
                                    event_date = (datetime.now() + timedelta(days=1)).date()
                                elif "today" in date_time_str.lower():
                                    event_date = datetime.now().date()
                                else:
                                    event_date = datetime.now().date()
                        
                        # Extract time portion
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}(?:AM|PM|am|pm))', date_time_str)
                        if time_match:
                            time_str = time_match.group(1)
                        else:
                            time_str = "TBA"
                    else:
                        event_date = datetime.now().date()
                        time_str = "TBA"
                    
                    # Extract location
                    location_elem = card.find(['span', 'div', 'p'], string=re.compile(r'Washington|DC|District of Columbia|Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Venue|Building|Place|Square|Court|Lane|Circle|Drive|Boulevard|Blvd', re.IGNORECASE))
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                    else:
                        location = "Location TBA"
                    
                    # For Meetup, assume all events in search results are free unless specified otherwise
                    is_free = True  # Meetup search results for "free" events should be free
                    
                    # Add event to list if it's free and not a duplicate
                    event_info = {
                        'title': title,
                        'link': link,
                        'date': event_date,
                        'time': time_str,
                        'location': location
                    }
                    events.append(event_info)
                    print(f"Added Meetup event: {title[:50]}...")
                
                except Exception as e:
                    print(f"Error processing Meetup event {i}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping Meetup events: {e}")
        
        finally:
            await browser.close()
    
    return events


async def scrape_luma_events(city: str) -> List[Dict]:
    """
    Scrape events from Luma based on city.
    """
    events = []
    
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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, timeout=30000)  # Changed from True to False to avoid detection
        page = await browser.new_page()
        
        try:
            print(f"Accessing Luma URL: {city_url}")
            await page.goto(city_url, wait_until="networkidle", timeout=30000)
            
            # Wait for content to load
            if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                await page.wait_for_timeout(5000)
            else:  # For pydoll Tab objects
                await asyncio.sleep(5.0)
            
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
            
            # Find event cards on Luma
            event_cards = soup.find_all('article', class_=re.compile(r'.*event.*', re.IGNORECASE))
            if not event_cards:
                event_cards = soup.find_all('div', class_=re.compile(r'.*event.*', re.IGNORECASE))
            
            print(f"Found {len(event_cards)} Luma event cards")
            
            for i, card in enumerate(event_cards[:30]):  # Limit to first 30 events
                try:
                    print(f"Processing Luma event {i+1}/{min(len(event_cards), 30)}")
                    
                    # Extract event title
                    title_elem = None

                    # Try multiple selectors for title
                    # Look for headings first (most likely to contain actual event title)
                    title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if not title_elem:
                        # Look for links that contain event information
                        link_elem = card.find('a', href=re.compile(r'/event/|/e/|event|show'))
                        if link_elem:
                            # Check for headings inside the link
                            title_in_link = link_elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if title_in_link:
                                title_elem = title_in_link
                            else:
                                # Use the link text itself if it's substantial
                                link_text = link_elem.get_text(strip=True)
                                if len(link_text) > 10:  # If it has substantial text, use it
                                    title_elem = link_elem
                    if not title_elem:
                        # Look for divs with title-like classes
                        title_elem = card.find('div', class_=re.compile(r'.*title.*|.*headline.*|.*event.*', re.IGNORECASE))
                    if not title_elem:
                        # Look for spans with title-like classes
                        title_elem = card.find('span', class_=re.compile(r'.*title.*|.*headline.*|.*event.*', re.IGNORECASE))
                    if not title_elem:
                        # Look for any element that might contain the title
                        # Look for elements with aria-label that might contain the title
                        aria_labels = card.find_all(attrs={"aria-label": True})
                        for elem in aria_labels:
                            if len(elem.get('aria-label', '')) > 10:
                                title_elem = elem
                                break
                    if not title_elem:
                        # Look for any text element that might contain the title
                        # Find the largest text element that looks like a title
                        all_text_elements = card.find_all(['div', 'span', 'p'])
                        for elem in all_text_elements:
                            text = elem.get_text(strip=True)
                            if len(text) > 15 and not re.search(r'almost full|sales end|going fast|save|share|attend|buy|tickets', text, re.IGNORECASE):
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
                    
                    # Extract event link
                    link_elem = None

                    # Look for links that contain event information
                    link_elem = card.find('a', href=re.compile(r'/event/|/e/|event|show'))
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
                    
                    # Extract date and time
                    date_elem = card.find(['time', 'span', 'div'], string=re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', re.IGNORECASE))
                    if date_elem:
                        date_time_str = date_elem.get_text(strip=True)
                        # Extract date portion
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
                                # Check for relative dates
                                if "tomorrow" in date_time_str.lower():
                                    event_date = (datetime.now() + timedelta(days=1)).date()
                                elif "today" in date_time_str.lower():
                                    event_date = datetime.now().date()
                                else:
                                    event_date = datetime.now().date()
                        
                        # Extract time portion
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}(?:AM|PM|am|pm))', date_time_str)
                        if time_match:
                            time_str = time_match.group(1)
                        else:
                            time_str = "TBA"
                    else:
                        event_date = datetime.now().date()
                        time_str = "TBA"
                    
                    # Extract location
                    location_elem = card.find(['span', 'div', 'p'], string=re.compile(r'Washington|DC|District of Columbia|Street|Ave|Avenue|Road|St|Plaza|Center|Hall|Venue|Building|Place|Square|Court|Lane|Circle|Drive|Boulevard|Blvd', re.IGNORECASE))
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                    else:
                        location = "Location TBA"
                    
                    # For Luma, assume all events are free unless specified otherwise
                    is_free = True
                    
                    # Add event to list if it's free and not a duplicate
                    event_info = {
                        'title': title,
                        'link': link,
                        'date': event_date,
                        'time': time_str,
                        'location': location
                    }
                    events.append(event_info)
                    print(f"Added Luma event: {title[:50]}...")
                
                except Exception as e:
                    print(f"Error processing Luma event {i}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping Luma events: {e}")
        
        finally:
            await browser.close()
    
    return events


def format_events_for_markdown(events: List[Dict], existing_content: str) -> str:
    """
    Format events into markdown format matching the existing structure.
    """
    if not events:
        return existing_content

    # Group events by date
    events_by_date = {}
    for event in events:
        date_key = event['date']
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(event)

    # Update the "Last Updated" line
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
        date_section_exists = f"## {date_header}" in updated_content

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
    
    return f"- **{clean_title}**\n\n  - Time: {event['time']}\n  - Location: {event['location']}\n  - Link: {event['link']}\n\n"


def read_existing_events(file_path: str) -> str:
    """
    Read the existing events file.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


async def main():
    """
    Main function to scrape events from various sources and update debug.md
    """
    print("Starting events scraper (debug mode)...")
    
    # Read existing content first
    file_path = "/home/workspace/Events/debug.md"  # Changed to debug.md
    existing_content = read_existing_events(file_path)
    
    all_events = []
    
    # Scrape from Meetup
    print("Scraping from Meetup...")
    meetup_location = "us--dc--washington"  # Correct format for Meetup
    meetup_events = await scrape_meetup_events(meetup_location, [], ["today", "tomorrow"])
    all_events.extend(meetup_events)
    print(f"Found {len(meetup_events)} Meetup events")
    
    # Scrape from Luma
    print("Scraping from Luma...")
    luma_city = "dc"  # Correct format for Luma
    luma_events = await scrape_luma_events(luma_city)
    all_events.extend(luma_events)
    print(f"Found {len(luma_events)} Luma events")
    
    print(f"Total events found: {len(all_events)}")
    
    if all_events:
        # Format events for markdown
        updated_content = format_events_for_markdown(all_events, existing_content)

        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        print(f"Successfully added {len(all_events)} events to {file_path}")
    else:
        print("No events found.")
    
    print("Scraping completed.")


if __name__ == "__main__":
    asyncio.run(main())