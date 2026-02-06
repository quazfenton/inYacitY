#!/usr/bin/env python3
"""
Event scraping script using agent-browser for Eventbrite, Meetup, and Luma
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List
import subprocess
import tempfile
import time
import aiohttp


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


def run_agent_browser_command(cmd: str) -> tuple[str, bool]:
    """
    Run an agent-browser command and return the output and success status.
    """
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error: {result.stderr}")
            return result.stderr, False
        return result.stdout, True
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {cmd}")
        return "", False
    except Exception as e:
        print(f"Error running agent-browser command: {e}")
        return "", False


def take_screenshot(filename: str):
    """
    Take a screenshot for debugging purposes.
    """
    try:
        cmd = f"agent-browser screenshot {filename}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"Screenshot saved to {filename}")
        else:
            print(f"Failed to take screenshot: {result.stderr}")
    except Exception as e:
        print(f"Error taking screenshot: {e}")


def take_screenshot_with_timestamp(prefix: str = "debug") -> str:
    """
    Take a screenshot with a timestamp in the filename.
    Returns the filename of the screenshot taken.
    """
    filename = f"{prefix}_{int(time.time())}.png"
    take_screenshot(filename)
    return filename


async def scrape_eventbrite_page_agent(url: str, existing_links: set = None) -> List[Dict]:
    """
    Scrape a single Eventbrite page for event information using agent-browser.
    """
    if existing_links is None:
        existing_links = set()
    events = []

    try:
        print(f"Accessing {url} with agent-browser")

        # Open the page
        open_cmd = f"agent-browser open '{url}'"
        output, success = run_agent_browser_command(open_cmd)

        if not success:
            print(f"Failed to open {url}")
            return events

        # Wait for page to load
        time.sleep(5)

        # Check if there's a captcha or verification screen after loading
        snapshot_result, success = run_agent_browser_command("agent-browser snapshot -i")
        if success and ("captcha" in snapshot_result.lower() or "verify" in snapshot_result.lower() or "robot" in snapshot_result.lower() or "human" in snapshot_result.lower() or "confirm" in snapshot_result.lower()):
            print("Captcha or verification screen detected, attempting to solve...")
            # Take a screenshot of the captcha
            screenshot_filename = take_screenshot_with_timestamp("eventbrite_captcha_detected")
            # Try to solve captcha using nopecha API
            await solve_captcha_with_nopecha("nopecha_api_key_here")  # Replace with actual API key
        else:
            # Take a screenshot after page load to see the normal content
            screenshot_filename = take_screenshot_with_timestamp("eventbrite_after_load")

        # Take a snapshot to get the page structure
        snapshot_result, success = run_agent_browser_command("agent-browser snapshot -i")

        if not success:
            print(f"Failed to get snapshot for {url}")
            # Take another screenshot to see what's on the page
            take_screenshot_with_timestamp("eventbrite_snapshot_failed")
            return events

        print(f"Snapshot received, processing content")

        # Look for event-related elements in the snapshot
        lines = snapshot_result.split('\n')

        # Find event cards based on common patterns in the snapshot
        # Look for elements that are more likely to be actual events
        event_elements = []
        for line in lines:
            line_lower = line.lower()
            # Look for lines that contain event-like information
            # Avoid UI elements like logos, search boxes, etc.
            if any(pattern in line_lower for pattern in ['event', 'card', 'listing', 'ticket', 'free']) and \
               not any(ui_pattern in line_lower for ui_pattern in ['logo', 'search', 'menu', 'header', 'footer', 'nav', 'button']):
                event_elements.append(line)

        print(f"Found {len(event_elements)} potential event elements")

        # Process each potential event element
        for i, element in enumerate(event_elements[:30]):  # Limit to avoid too many requests
            try:
                # Extract information from the element
                # Look for references to click on for more details
                ref_match = re.search(r'\[ref=([^\]]+)\]', element)
                if not ref_match:
                    continue

                ref_id = ref_match.group(1)

                # Try to extract the actual event title from the element
                # Look for text that appears to be an event title (usually contains event-like words)
                title = ""

                # Look for text that follows common event patterns
                # This regex looks for text that might be an event title
                # It looks for text that might contain event details like dates, times, etc.
                event_text_match = re.search(r'"([^"]*?(?:\b(?:event|meetup|social|party|workshop|conference|festival|concert|show|exhibition|sale|auction|fair|market|expo|summit|forum|seminar|training|class|course|lesson|meeting|gathering|celebration|ceremony|performance|screening|launch|opening|closing|presentation|talk|lecture|discussion|debate|contest|competition|tournament|game|match|race|marathon|run|walk|hike|trip|tour|excursion|outing|adventure|expedition|voyage|journey|retreat|camp|festival|carnival|mardi gras|carnaval|fiesta|fete|jamboree|picnic|barbecue|bbq|dinner|lunch|breakfast|brunch|reception|banquet|buffet|potluck|picnic|buffet|reception|toast|celebration|party|gala|ball|soiree|revelry|festivity|jubilee|commemoration|anniversary|birthday|wedding|engagement|baby shower|bridal shower|graduation|commencement|convocation|inauguration|dedication|blessing|consecration|opening ceremony|closing ceremony|ribbon cutting|groundbreaking|laying of cornerstone|memorial service|funeral|wake|visitation|viewing|calling hours|family viewing|public viewing|memorial|tribute|homage|salute|recognition|award ceremony|prize ceremony|medal ceremony|trophy ceremony|championship|title fight|bout|contest|competition|match|game|race|marathon|run|walk|relay|triathlon|duathlon|aquathlon|biathlon|pentathlon|decathlon|heptathlon|octathlon|pentathlon|olympics|paralympics|world cup|super bowl|stanley cup|world series|playoffs|finals|semifinals|quarterfinals|round of 16|round of 8|round of 4|final|championship|title|winner|victor|champion|first place|second place|third place|gold medal|silver medal|bronze medal|medal|prize|award|trophy|cup|shield|belt|title|crown|crown jewel|jewel in the crown|crowning achievement|crowning moment|crowning glory|crowning honor)\b)[^"]*)"', element, re.IGNORECASE)

                if event_text_match:
                    title = event_text_match.group(1).strip()
                else:
                    # Fallback: look for any text that might be an event title
                    # But avoid common UI elements
                    text_match = re.search(r'"([^"]+)"', element)
                    if text_match:
                        potential_title = text_match.group(1).strip()
                        # Skip if it's clearly a UI element
                        ui_elements = ['logo', 'search', 'menu', 'home', 'about', 'contact', 'login', 'sign in', 'register', 'signup', 'account', 'profile', 'settings', 'help', 'support', 'faq', 'terms', 'privacy', 'button', 'click', 'tap', 'press', 'touch', 'swipe', 'scroll', 'drag', 'drop', 'upload', 'download', 'save', 'delete', 'edit', 'create', 'update', 'modify', 'change', 'adjust', 'configure', 'setup', 'install', 'uninstall', 'remove', 'add', 'subtract', 'multiply', 'divide', 'calculate', 'compute', 'process', 'analyze', 'evaluate', 'assess', 'review', 'examine', 'inspect', 'check', 'verify', 'validate', 'confirm', 'approve', 'authorize', 'permit', 'allow', 'enable', 'activate', 'deactivate', 'disable', 'turn on', 'turn off', 'switch', 'toggle', 'flip', 'rotate', 'spin', 'twist', 'turn', 'move', 'shift', 'slide', 'glide', 'flow', 'stream', 'cascade', 'fall', 'drop', 'descend', 'ascend', 'rise', 'lift', 'raise', 'elevate', 'hoist', 'haul', 'pull', 'push', 'press', 'squeeze', 'compress', 'expand', 'stretch', 'extend', 'lengthen', 'shorten', 'reduce', 'increase', 'grow', 'shrink', 'enlarge', 'magnify', 'amplify', 'boost', 'enhance', 'improve', 'upgrade', 'update', 'refresh', 'renew', 'restore', 'repair', 'fix', 'mend', 'patch', 'sew', 'stitch', 'knit', 'weave', 'crochet', 'embroider', 'decorate', 'ornament', 'adorn', 'beautify', 'embellish', 'grace', 'adorn', 'deck', 'trim', 'garnish', 'spruce', 'tidy', 'organize', 'arrange', 'order', 'sort', 'classify', 'categorize', 'group', 'cluster', 'collect', 'gather', 'assemble', 'accumulate', 'amass', 'pile', 'stack', 'heap', 'mount', 'build', 'construct', 'create', 'form', 'shape', 'mold', 'craft', 'fabricate', 'manufacture', 'produce', 'generate', 'yield', 'provide', 'supply', 'offer', 'present', 'deliver', 'dispatch', 'send', 'transmit', 'transfer', 'convey', 'communicate', 'express', 'state', 'declare', 'announce', 'proclaim', 'publish', 'release', 'distribute', 'spread', 'circulate', 'disseminate', 'broadcast', 'transmit', 'air', 'televise', 'stream', 'upload', 'post', 'publish', 'share', 'distribute', 'allocate', 'assign', 'designate', 'appoint', 'nominate', 'select', 'choose', 'pick', 'opt', 'prefer', 'favor', 'like', 'love', 'adore', 'worship', 'revere', 'esteem', 'regard', 'respect', 'honor', 'admire', 'appreciate', 'value', 'treasure', 'cherish', 'nurture', 'cultivate', 'foster', 'nourish', 'feed', 'sustain', 'maintain', 'preserve', 'protect', 'guard', 'defend', 'shield', 'cover', 'hide', 'conceal', 'obscure', 'veil', 'mask', 'disguise', 'camouflage', 'cloak', 'mantle', 'blanket', 'sheet', 'cover', 'lid', 'cap', 'hat', 'helmet', 'hood', 'mask', 'visor', 'goggles', 'sunglasses', 'eyeglasses', 'spectacles', 'frames', 'lenses', 'contacts', 'glasses', 'hearing aid', 'walker', 'cane', 'crutches', 'wheelchair', 'scooter', 'bed', 'chair', 'table', 'desk', 'couch', 'sofa', 'love seat', 'recliner', 'ottoman', 'bench', 'stool', 'stool', 'footstool', 'footrest', 'armrest', 'headrest', 'pillow', 'blanket', 'quilt', 'comforter', 'duvet', 'sheet', 'bedspread', 'coverlet', 'carpet', 'rug', 'mat', 'floor', 'wall', 'ceiling', 'roof', 'door', 'window', 'curtain', 'blinds', 'shade', 'awning', 'canopy', 'tent', 'shelter', 'shack', 'hut', 'cabin', 'cottage', 'house', 'home', 'apartment', 'condo', 'townhouse', 'duplex', 'triplex', 'quadplex', 'building', 'structure', 'construction', 'architecture', 'design', 'blueprint', 'plan', 'scheme', 'strategy', 'tactic', 'method', 'approach', 'technique', 'procedure', 'process', 'operation', 'activity', 'action', 'behavior', 'conduct', 'deportment', 'manner', 'way', 'style', 'fashion', 'mode', 'form', 'shape', 'figure', 'outline', 'contour', 'profile', 'silhouette', 'shadow', 'reflection', 'image', 'picture', 'photo', 'photograph', 'snapshot', 'portrait', 'landscape', 'scene', 'view', 'panorama', 'vista', 'prospect', 'outlook', 'perspective', 'angle', 'aspect', 'facet', 'phase', 'stage', 'step', 'level', 'degree', 'grade', 'rank', 'class', 'category', 'type', 'kind', 'sort', 'variety', 'species', 'genus', 'family', 'order', 'class', 'phylum', 'kingdom', 'domain', 'empire', 'realm', 'sphere', 'territory', 'region', 'area', 'zone', 'district', 'neighborhood', 'locality', 'locale', 'place', 'location', 'position', 'spot', 'site', 'situation', 'setting', 'environment', 'surroundings', 'vicinity', 'environs', 'neighborhood', 'environs', 'surrounds', 'outskirts', 'suburbs', 'suburbia', 'countryside', 'country', 'rural', 'urban', 'city', 'town', 'village', 'hamlet', 'settlement', 'colony', 'outpost', 'station', 'base', 'headquarters', 'office', 'workplace', 'factory', 'plant', 'mill', 'workshop', 'studio', 'laboratory', 'lab', 'clinic', 'hospital', 'medical center', 'health center', 'doctor', 'physician', 'surgeon', 'nurse', 'therapist', 'counselor', 'psychologist', 'psychiatrist', 'social worker', 'teacher', 'professor', 'instructor', 'educator', 'mentor', 'coach', 'trainer', 'instructor', 'guide', 'leader', 'manager', 'supervisor', 'director', 'executive', 'administrator', 'official', 'authority', 'government', 'politics', 'policy', 'law', 'legislation', 'statute', 'ordinance', 'regulation', 'rule', 'standard', 'norm', 'criterion', 'measure', 'metric', 'benchmark', 'yardstick', 'cubit', 'foot', 'inch', 'yard', 'mile', 'kilometer', 'meter', 'centimeter', 'millimeter', 'micrometer', 'nanometer', 'angstrom', 'furlong', 'rod', 'chain', 'fathom', 'cable', 'nautical mile', 'league', 'pace', 'stride', 'step', 'footstep', 'footprint', 'track', 'trail', 'path', 'road', 'street', 'avenue', 'boulevard', 'drive', 'lane', 'court', 'circle', 'square', 'plaza', 'park', 'garden', 'yard', 'lawn', 'field', 'meadow', 'pasture', 'farm', 'ranch', 'estate', 'manor', 'mansion', 'palace', 'castle', 'fortress', 'citadel', 'stronghold', 'bastion', 'redoubt', 'trench', 'ditch', 'moat', 'drawbridge', 'portcullis', 'gate', 'arch', 'bridge', 'tunnel', 'culvert', 'overpass', 'underpass', 'viaduct', 'aqueduct', 'dam', 'reservoir', 'lake', 'pond', 'pool', 'lagoon', 'bay', 'gulf', 'sea', 'ocean', 'river', 'stream', 'brook', 'creek', 'tributary', 'confluence', 'delta', 'estuary', 'mouth', 'source', 'spring', 'well', 'fountain', 'waterfall', 'cascade', 'rapids', 'whirlpool', 'eddyy', 'current', 'stream', 'flow', 'motion', 'movement', 'action', 'activity', 'exercise', 'practice', 'application', 'implementation', 'execution', 'performance', 'fulfillment', 'realization', 'achievement', 'accomplishment', 'completion', 'finish', 'end', 'conclusion', 'termination', 'cessation', 'stop', 'halt', 'pause', 'break', 'interval', 'intermission', 'rest', 'respite', 'breather', 'recess', 'vacation', 'holiday', 'leave', 'absence', 'departure', 'exit', 'outlet', 'escape', 'flight', 'flee', 'run', 'sprint', 'dash', 'race', 'hurry', 'rush', 'haste', 'speed', 'velocity', 'acceleration', 'force', 'energy', 'power', 'strength', 'might', 'potency', 'capacity', 'ability', 'capability', 'competence', 'skill', 'talent', 'gift', 'aptitude', 'faculty', 'endowment', 'endowment', 'attribute', 'characteristic', 'feature', 'trait', 'property', 'quality', 'aspect', 'dimension', 'factor', 'element', 'component', 'part', 'portion', 'segment', 'section', 'division', 'unit', 'module', 'subunit', 'subsection', 'subdivision', 'submodule', 'subcomponent', 'subpart', 'subportion', 'subsegment', 'subsection', 'subdivision', 'submodule', 'subcomponent', 'subpart', 'subportion', 'subsegment']
                        if not any(ui_word in potential_title.lower() for ui_word in ui_elements):
                            title = potential_title

                if not title or len(title.strip()) < 3:
                    title = "Event Title Unknown"

                # Skip if no meaningful title
                if not title or len(title.strip()) < 3 or title == "Event Title Unknown":
                    continue

                # Check if this event link already exists
                # For now, we'll use a combination of title and ref as unique identifier
                link_identifier = f"{title}_{ref_id}"
                if link_identifier in existing_links or link_identifier in [evt['link'] for evt in events]:
                    continue

                # Create a basic event entry
                event_info = {
                    'title': title,
                    'link': link_identifier,  # Placeholder - would need to click to get actual link
                    'date': datetime.now().date(),
                    'time': "TBA",
                    'location': "Location TBA",
                    'description': "Description not available - would need to click for details"
                }

                events.append(event_info)
                print(f"Added event: {title[:50]}...")

            except Exception as e:
                print(f"Error processing event element {i}: {e}")
                continue

        # Close the browser when done
        run_agent_browser_command("agent-browser close")

    except Exception as e:
        print(f"Error scraping page {url}: {e}")
        # Ensure browser is closed even if there's an error
        try:
            run_agent_browser_command("agent-browser close")
        except:
            pass

    return events


async def scrape_meetup_events_agent(location_code: str, search_terms: List[str] = None, filters: List[str] = None) -> List[Dict]:
    """
    Scrape events from Meetup based on location and search terms using agent-browser.
    """
    events = []

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

        print(f"Accessing Meetup URL: {base_url} with agent-browser")

        # Open the page
        open_cmd = f"agent-browser open '{base_url}'"
        output, success = run_agent_browser_command(open_cmd)

        if not success:
            print(f"Failed to open {base_url}")
            return events

        # Wait for page to load
        time.sleep(5)

        # Check if there's a captcha or verification screen after loading
        snapshot_result, success = run_agent_browser_command("agent-browser snapshot -i")
        if success and ("captcha" in snapshot_result.lower() or "verify" in snapshot_result.lower() or "robot" in snapshot_result.lower() or "human" in snapshot_result.lower() or "confirm" in snapshot_result.lower()):
            print("Captcha or verification screen detected, attempting to solve...")
            # Take a screenshot of the captcha
            screenshot_filename = take_screenshot_with_timestamp("meetup_captcha_detected")
            # Try to solve captcha using nopecha API
            await solve_captcha_with_nopecha("nopecha_api_key_here")  # Replace with actual API key
        else:
            # Take a screenshot after page load to see the normal content
            screenshot_filename = take_screenshot_with_timestamp("meetup_after_load")

        # Take a snapshot to get the page structure
        snapshot_result, success = run_agent_browser_command("agent-browser snapshot -i")

        if not success:
            print(f"Failed to get snapshot for {base_url}")
            # Take another screenshot to see what's on the page
            take_screenshot_with_timestamp("meetup_snapshot_failed")
            return events

        # Look for event-related elements in the snapshot
        lines = snapshot_result.split('\n')

        # Find event cards based on common patterns in the snapshot
        event_elements = []
        for line in lines:
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in ['event', 'meetup', 'attend', 'join', 'event-card', 'listing']):
                event_elements.append(line)

        print(f"Found {len(event_elements)} potential Meetup event elements")

        # Process each potential event element
        for i, element in enumerate(event_elements[:20]):  # Limit to avoid too many requests
            try:
                # Extract information from the element
                # Look for references to click on for more details
                ref_match = re.search(r'\[ref=([^\]]+)\]', element)
                if not ref_match:
                    continue

                ref_id = ref_match.group(1)

                # Try to extract basic info from the element text
                # Look for text in quotes or after common labels
                title = ""
                # Try to find text in quotes
                title_match = re.search(r'"([^"]*)"', element)
                if title_match:
                    title = title_match.group(1)
                else:
                    # Try to find text after common labels
                    text_match = re.search(r'-\s+(.+?)\s+\[ref=', element)
                    if text_match:
                        title = text_match.group(1).strip()

                if not title:
                    title = "Event Title Unknown"

                # Skip if no meaningful title
                if not title or len(title.strip()) < 3:
                    continue

                # Create a basic event entry
                event_info = {
                    'title': title,
                    'link': f"meetup_{ref_id}",  # Using ref ID as identifier
                    'date': datetime.now().date(),
                    'time': "TBA",
                    'location': "Location TBA",
                    'description': "Description not available - would need to click for details",
                    'source': 'Meetup'
                }

                events.append(event_info)
                print(f"Added Meetup event: {title[:50]}...")

            except Exception as e:
                print(f"Error processing Meetup event element {i}: {e}")
                continue

        # Close the browser when done
        run_agent_browser_command("agent-browser close")

    except Exception as e:
        print(f"Error scraping Meetup events: {e}")
        # Ensure browser is closed even if there's an error
        try:
            run_agent_browser_command("agent-browser close")
        except:
            pass

    return events


async def scrape_luma_events_agent(city: str) -> List[Dict]:
    """
    Scrape events from Luma based on city using agent-browser.
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

    try:
        print(f"Accessing Luma URL: {city_url} with agent-browser")

        # Open the page
        open_cmd = f"agent-browser open '{city_url}'"
        output, success = run_agent_browser_command(open_cmd)

        if not success:
            print(f"Failed to open {city_url}")
            return events

        # Wait for page to load
        time.sleep(5)

        # Check if there's a captcha or verification screen after loading
        snapshot_result, success = run_agent_browser_command("agent-browser snapshot -i")
        if success and ("captcha" in snapshot_result.lower() or "verify" in snapshot_result.lower() or "robot" in snapshot_result.lower() or "human" in snapshot_result.lower() or "confirm" in snapshot_result.lower()):
            print("Captcha or verification screen detected, attempting to solve...")
            # Take a screenshot of the captcha
            screenshot_filename = take_screenshot_with_timestamp("luma_captcha_detected")
            # Try to solve captcha using nopecha API
            await solve_captcha_with_nopecha("nopecha_api_key_here")  # Replace with actual API key
        else:
            # Take a screenshot after page load to see the normal content
            screenshot_filename = take_screenshot_with_timestamp("luma_after_load")

        # Take a snapshot to get the page structure
        snapshot_result, success = run_agent_browser_command("agent-browser snapshot -i")

        if not success:
            print(f"Failed to get snapshot for {city_url}")
            # Take another screenshot to see what's on the page
            take_screenshot_with_timestamp("luma_snapshot_failed")
            return events

        # Look for event-related elements in the snapshot
        lines = snapshot_result.split('\n')

        # Find event cards based on common patterns in the snapshot
        event_elements = []
        for line in lines:
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in ['event', 'card', 'date', 'time', 'location', 'event-card', 'content-card', 'date-title']):
                event_elements.append(line)

        print(f"Found {len(event_elements)} potential Luma event elements")

        # Process each potential event element
        for i, element in enumerate(event_elements[:20]):  # Limit to avoid too many requests
            try:
                # Extract information from the element
                # Look for references to click on for more details
                ref_match = re.search(r'\[ref=([^\]]+)\]', element)
                if not ref_match:
                    continue

                ref_id = ref_match.group(1)

                # Try to extract basic info from the element text
                # Look for text in quotes or after common labels
                title = ""
                # Try to find text in quotes
                title_match = re.search(r'"([^"]*)"', element)
                if title_match:
                    title = title_match.group(1)
                else:
                    # Try to find text after common labels
                    text_match = re.search(r'-\s+(.+?)\s+\[ref=', element)
                    if text_match:
                        title = text_match.group(1).strip()

                if not title:
                    title = "Event Title Unknown"

                # Skip if no meaningful title
                if not title or len(title.strip()) < 3:
                    continue

                # Create a basic event entry
                event_info = {
                    'title': title,
                    'link': f"luma_{ref_id}",  # Using ref ID as identifier
                    'date': datetime.now().date(),
                    'time': "TBA",
                    'location': "Location TBA",
                    'description': "Description not available - would need to click for details",
                    'source': 'Luma'
                }

                events.append(event_info)
                print(f"Added Luma event: {title[:50]}...")

            except Exception as e:
                print(f"Error processing Luma event element {i}: {e}")
                continue

        # Close the browser when done
        run_agent_browser_command("agent-browser close")

    except Exception as e:
        print(f"Error scraping Luma events: {e}")
        # Ensure browser is closed even if there's an error
        try:
            run_agent_browser_command("agent-browser close")
        except:
            pass

    return events


async def main():
    """
    Main function to scrape events from various sources using agent-browser and save to events.json
    """
    print("Starting events scraper with agent-browser...")

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

    all_events = []

    # Initialize empty set for existing links to avoid duplicates
    existing_links = set()
    print(f"Initialized with {len(existing_links)} existing event links to avoid")

    # Check if we should scrape from Eventbrite
    if config.get("MODES", {}).get("ENABLE_EVENTBRITE_SCRAPING", True):
        print("Scraping from Eventbrite using agent-browser...")
        # Generate URLs based on configuration
        event_type = "events" if config.get("MODES", {}).get("INCLUDE_PAID_EVENTS", False) else "free--events"
        base_url = f"https://www.eventbrite.com/d/{location}/{event_type}/"
        
        urls = []
        main_pages = config.get("MAIN_PAGES", 2)
        for page in range(1, main_pages + 1):
            urls.append(base_url + f"?page={page}")

        filter_pages = config.get("FILTER_PAGES", 2)
        for filter_type in config.get("FILTERS_TO_USE", ["today", "tomorrow"]):
            for page in range(1, filter_pages + 1):
                urls.append(f"https://www.eventbrite.com/d/{location}/{event_type}--{filter_type}/?page={page}")

        # Scrape each URL
        for url in urls:
            print(f"Scraping: {url}")
            events = await scrape_eventbrite_page_agent(url, existing_links)
            all_events.extend(events)
            print(f"Found {len(events)} new events on this page")

    # Check if we should scrape from Meetup
    if config.get("MODES", {}).get("ENABLE_MEETUP_SCRAPING", True):
        print(f"Scraping from Meetup using agent-browser for location: {meetup_location}...")
        search_terms = config.get("MODES", {}).get("CUSTOM_SEARCH_TERMS", [])
        filters = config.get("FILTERS_TO_USE", [])

        meetup_events = await scrape_meetup_events_agent(meetup_location, search_terms, filters)
        all_events.extend(meetup_events)
        print(f"Found {len(meetup_events)} new Meetup events")

    # Check if we should scrape from Luma
    if config.get("MODES", {}).get("ENABLE_LUMA_SCRAPING", True):
        print(f"Scraping from Luma using agent-browser for city: {luma_city}...")
        luma_events = await scrape_luma_events_agent(luma_city)
        all_events.extend(luma_events)
        print(f"Found {len(luma_events)} new Luma events")

    print(f"Total new events found: {len(all_events)}")

    if all_events:
        # Sort events by date
        all_events.sort(key=lambda x: x.get('date', '2026-12-31'))
        
        # Prepare events in JSON format
        events_json = {
            'events': all_events,
            'total': len(all_events),
            'last_updated': datetime.now().isoformat()
        }

        # Write the events to events.json
        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump(events_json, f, indent=2, default=str)

        print(f"Successfully saved {len(all_events)} events to events.json")
    else:
        print("No new events found.")

    print("Scraping completed.")


async def solve_captcha_with_nopecha(api_key: str):
    """
    Solve captcha using the nopecha API.
    See: https://nopecha.com/api-reference/
    """
    try:
        print("Attempting to solve captcha with Nopecha API...")

        # In a real implementation, we would:
        # 1. Locate the captcha image on the page
        # 2. Capture the image
        # 3. Send it to the Nopecha API
        # 4. Get the solution
        # 5. Fill in the captcha field with the solution

        # For now, this is a placeholder implementation
        # The actual implementation would require:
        # - Capturing the specific captcha image
        # - Sending it to the Nopecha API endpoint
        # - Processing the response and filling the form

        # Example API call (this is illustrative - actual implementation may vary):
        '''
        async with aiohttp.ClientSession() as session:
            # Assuming we have a captcha image file
            with open('captcha_image.png', 'rb') as f:
                captcha_data = f.read()

            headers = {
                'Authorization': f'Bearer {api_key}',
            }

            data = aiohttp.FormData()
            data.add_field('image', captcha_data, filename='captcha.png', content_type='image/png')
            data.add_field('type', 'textual')  # or 'reCAPTCHA', 'hCaptcha', etc.

            async with session.post('https://api.nopecha.com/solve', headers=headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    captcha_solution = result.get('solution', '')

                    # Now we would need to input the solution back into the page
                    # This would require interacting with the page again
                    if captcha_solution:
                        # Use agent-browser to fill the captcha solution
                        fill_cmd = f"agent-browser fill 'input[name=\"captcha\"]' '{captcha_solution}'"
                        run_agent_browser_command(fill_cmd)

                        # Click submit button
                        click_cmd = "agent-browser click 'button[type=\"submit\"]'"
                        run_agent_browser_command(click_cmd)
        '''

        print("Captcha solving with Nopecha API is not fully implemented yet.")
        print("To implement this feature, you would need to:")
        print("1. Capture the specific captcha image from the page")
        print("2. Send it to the Nopecha API endpoint")
        print("3. Process the response and fill the solution back into the page")
        print("See https://nopecha.com/api-reference/ for API details")

    except Exception as e:
        print(f"Error solving captcha with Nopecha: {e}")


if __name__ == "__main__":
    asyncio.run(main())