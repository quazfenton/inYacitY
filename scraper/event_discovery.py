#!/usr/bin/env python3
"""
Event Discovery Module - Keyword-based link discovery and social search.

Finds events from platforms without dedicated scrapers (partiful, ra.co, posh.vip)
using:
  1. Scira API (X/Twitter search) - quality-filtered, requires time+location pairing
  2. Direct keyword search via Firecrawl/Hyperbrowser for event platform links

Quality filters:
  - Time keywords (tonight, tomorrow, Friday, this weekend) must be paired with location
  - Excludes domains with working scrapers (eventbrite, meetup, luma, dice)
  - Prioritizes high-value event platform links
"""

import asyncio
import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup

# API Keys
SCIRA_API_KEY = os.environ.get("SCIRA_API_KEY")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
HYPERBROWSER_API_KEY = os.environ.get("HYPERBROWSER_API_KEY")

# Domains with working scrapers - EXCLUDE from discovery to avoid duplication
EXCLUDED_DOMAINS = {
    "eventbrite.com",
    "www.eventbrite.com",
    "meetup.com",
    "www.meetup.com",
    "lu.ma",
    "luma.com",
    "dice.fm",
    "dice.seatgeek.com",
}

# High-value event platforms to prioritize (no working scrapers yet)
HIGH_VALUE_PLATFORMS = [
    "partiful.com",
    "www.partiful.com",
    "ra.co",
    "www.ra.co",
    "posh.vip",
    "www.posh.vip",
    "ticketfly.com",
    "www.ticketfly.com",
    "songkick.com",
    "www.songkick.com",
    "bandsintown.com",
    "www.bandsintown.com",
    "facebook.com/events",
    "www.facebook.com/events",
    "residentadvisor.net",
    "www.residentadvisor.net",
]

# Time keywords that indicate event timing
TIME_KEYWORDS = ["tonight", "tomorrow", "friday", "saturday", "sunday", "this weekend", "weekend"]

# High-value event keywords
EVENT_KEYWORDS = [
    "party",
    "venue",
    "event",
    "show",
    "live",
    "concert",
    "dj",
    "set",
    "night",
    "club",
    "rave",
    "underground",
    "pop-up",
    "popup",
    "warehouse",
    "gallery",
    "opening",
    "launch",
    "festival",
]

# City name mapping from config slug to display name
CITY_DISPLAY_NAMES = {
    "ca--los-angeles": "Los Angeles",
    "ny--new-york": "New York",
    "dc--washington": "Washington DC",
    "fl--miami": "Miami",
    "tx--houston": "Houston",
    "il--chicago": "Chicago",
    "az--phoenix": "Phoenix",
    "pa--philadelphia": "Philadelphia",
    "tx--san-antonio": "San Antonio",
    "ca--san-diego": "San Diego",
    "tx--dallas": "Dallas",
    "tx--austin": "Austin",
    "wa--seattle": "Seattle",
    "co--denver": "Denver",
    "ma--boston": "Boston",
    "ga--atlanta": "Atlanta",
    "nv--las-vegas": "Las Vegas",
    "mi--detroit": "Detroit",
    "or--portland": "Portland",
    "nc--charlotte": "Charlotte",
    "tn--nashville": "Nashville",
    "ok--oklahoma-city": "Oklahoma City",
    "la--new-orleans": "New Orleans",
    "fl--orlando": "Orlando",
    "fl--tampa": "Tampa",
    "ca--san-jose": "San Jose",
    "ca--san-francisco": "San Francisco",
    "ny--buffalo": "Buffalo",
    "oh--columbus": "Columbus",
    "oh--cleveland": "Cleveland",
    "in--indianapolis": "Indianapolis",
    "mo--kansas-city": "Kansas City",
    "mo--st-louis": "St. Louis",
    "ca--sacramento": "Sacramento",
    "tx--fort-worth": "Fort Worth",
    "va--richmond": "Richmond",
    "mn--minneapolis": "Minneapolis",
    "wi--milwaukee": "Milwaukee",
    "ky--louisville": "Louisville",
    "sc--charleston": "Charleston",
    "al--birmingham": "Birmingham",
    "ut--salt-lake-city": "Salt Lake City",
    "nm--albuquerque": "Albuquerque",
}


def _get_city_display_name(city_slug: str) -> str:
    """Get display name for a city slug."""
    return CITY_DISPLAY_NAMES.get(city_slug, city_slug.replace("--", " ").title())


def _get_day_of_week() -> str:
    """Get current day of week lowercase."""
    return datetime.now().strftime("%A").lower()


def _is_excluded_domain(url: str) -> bool:
    """Check if URL belongs to a domain with a working scraper."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in EXCLUDED_DOMAINS)


def _is_high_value_platform(url: str) -> bool:
    """Check if URL belongs to a high-value platform without a working scraper."""
    url_lower = url.lower()
    return any(platform in url_lower for platform in HIGH_VALUE_PLATFORMS)


def _quality_score(text: str, city_display: str) -> float:
    """
    Score text quality for event relevance.
    Returns 0.0-1.0 where higher is better.
    """
    if not text:
        return 0.0

    text_lower = text.lower()
    score = 0.0

    # Time keyword + location pairing (high value)
    has_time_keyword = any(kw in text_lower for kw in TIME_KEYWORDS)
    has_location = city_display.lower() in text_lower

    if has_time_keyword and has_location:
        score += 0.4

    # High-value event keywords
    event_matches = sum(1 for kw in EVENT_KEYWORDS if kw in text_lower)
    score += min(0.3, event_matches * 0.1)

    # Platform bonus
    if any(p in text_lower for p in HIGH_VALUE_PLATFORMS):
        score += 0.2

    # Location match
    if has_location:
        score += 0.1

    return min(1.0, score)


def _extract_events_from_html(html: str, city_slug: str, source: str = "discovery") -> List[Dict]:
    """Extract event-like data from HTML content."""
    events = []
    city_display = _get_city_display_name(city_slug)

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return events

    # Find all links
    links = soup.find_all("a", href=True)

    for link in links:
        href = link.get("href", "")
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        # Skip excluded domains
        if _is_excluded_domain(href):
            continue

        # Only process high-value platforms
        if not _is_high_value_platform(href):
            continue

        # Get surrounding text for quality scoring
        parent = link.parent
        context_text = ""
        if parent:
            context_text = parent.get_text(" ", strip=True)
        if link.next_sibling:
            context_text += " " + str(link.next_sibling)

        # Score quality
        quality = _quality_score(context_text, city_display)

        # Only include if quality threshold met (time+location or event keywords)
        if quality < 0.3:
            continue

        # Extract title from link text or surrounding context
        title = link.get_text(" ", strip=True)
        if not title and context_text:
            title = context_text[:100]

        if not title:
            continue

        # Normalize URL
        if href.startswith("/"):
            if "ra.co" in href:
                href = "https://ra.co" + href
            elif "posh.vip" in href:
                href = "https://posh.vip" + href
            elif "partiful.com" in href:
                href = "https://partiful.com" + href

        # Try to extract date from context
        date_str = ""
        time_str = "TBA"
        location_str = "Location TBA"

        # Look for date patterns in context
        date_patterns = [
            r"(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(\w+ \d{1,2}(?:st|nd|rd|th)?)",
            r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                break

        # Look for time patterns
        time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))", context_text)
        if time_match:
            time_str = time_match.group(1)

        # Look for venue/location
        venue_patterns = [r"at\s+([A-Z][\w\s&]+?)(?:\||,|$)", r"venue[:\s]+([^\n]+)"]
        for pattern in venue_patterns:
            match = re.search(pattern, context_text)
            if match:
                location_str = match.group(1).strip()
                break

        events.append({
            "title": title[:200],
            "link": href,
            "date": date_str or "",
            "time": time_str,
            "location": location_str,
            "description": context_text[:500] if context_text else "Event discovered via keyword search",
            "source": source,
            "city": city_slug,
            "quality_score": round(quality, 2),
        })

    return events


async def search_with_scira(city_slug: str, max_results: int = 20) -> List[Dict]:
    """
    Use Scira API to search X/Twitter for events in a city.
    TOGGLED OFF by default - low quality / rare finds.
    """
    if not SCIRA_API_KEY:
        return []

    city_display = _get_city_display_name(city_slug)
    day = _get_day_of_week()

    # Build search queries - location + time keyword pairing required
    queries = [
        f"{city_display} tonight party link:partiful.com",
        f"{city_display} tomorrow event link:partiful.com",
        f"{city_display} {day} link:ra.co",
        f"{city_display} this weekend link:posh.vip",
        f"{city_display} tonight underground",
        f"{city_display} {day} night event",
    ]

    events = []

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    headers = {
                        "Authorization": f"Bearer {SCIRA_API_KEY}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "query": query,
                        "max_results": max_results // len(queries),
                        "filter": "latest",
                    }

                    async with session.post(
                        "https://api.scira.ai/v1/search",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status != 200:
                            continue

                        data = await resp.json()

                        # Parse results
                        results = data.get("results") or data.get("tweets") or data.get("data") or []
                        for result in results:
                            text = result.get("text") or result.get("content") or ""
                            url = result.get("url") or result.get("link") or ""

                            # Extract URLs from text if not provided
                            if not url:
                                url_matches = re.findall(r"https?://[^\s]+", text)
                                if url_matches:
                                    url = url_matches[0]

                            if not url or _is_excluded_domain(url):
                                continue

                            quality = _quality_score(text, city_display)
                            if quality < 0.3:
                                continue

                            events.append({
                                "title": text[:150],
                                "link": url,
                                "date": "",
                                "time": "TBA",
                                "location": "Location TBA",
                                "description": text[:500],
                                "source": "scira_x",
                                "city": city_slug,
                                "quality_score": round(quality, 2),
                            })

                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"  Scira query failed: {query[:50]}... - {e}")

    except Exception as e:
        print(f"  Scira search failed: {e}")

    return events


async def search_with_firecrawl(city_slug: str, max_results: int = 15) -> List[Dict]:
    """
    Use Firecrawl to search for event platform links with location + time keywords.
    Searches Google/Bing for high-value platform links.
    """
    if not FIRECRAWL_API_KEY:
        return []

    city_display = _get_city_display_name(city_slug)
    day = _get_day_of_week()

    # Build search queries - location + time keyword required
    search_queries = [
        f"site:partiful.com {city_display} tonight",
        f"site:partiful.com {city_display} this weekend",
        f"site:ra.co/events {city_display}",
        f"site:posh.vip/events {city_display}",
        f"site:partiful.com {city_display} {day}",
        f"site:ra.co {city_display} party tonight",
    ]

    events = []

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for query in search_queries:
                try:
                    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}"}
                    payload = {
                        "url": f"https://www.google.com/search?q={query}",
                        "formats": ["html"],
                        "onlyMainContent": True,
                        "maxAge": 86400,
                    }

                    async with session.post(
                        "https://api.firecrawl.dev/v2/scrape",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=45)
                    ) as resp:
                        if resp.status != 200:
                            continue

                        data = await resp.json()
                        html = data.get("html", "")
                        if not html:
                            continue

                        page_events = _extract_events_from_html(html, city_slug, source="firecrawl_search")
                        events.extend(page_events)

                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"  Firecrawl search failed: {query[:50]}... - {e}")

    except Exception as e:
        print(f"  Firecrawl search failed: {e}")

    return events


async def scrape_platform_listing(city_slug: str, platform: str) -> List[Dict]:
    """
    Directly scrape a platform's city listing page using browser.py fallback chain.
    Platforms: partiful, ra.co, posh.vip
    """
    from browser import fetch_page

    events = []
    city_display = _get_city_display_name(city_slug)

    platform_urls = {
        "partiful": f"https://partiful.com/search?q={city_display.replace(' ', '+')}",
        "ra.co": f"https://ra.co/events/{_get_ra_co_location(city_slug)}",
        "posh.vip": f"https://posh.vip/events/{_get_posh_vip_location(city_slug)}",
    }

    url = platform_urls.get(platform)
    if not url:
        return events

    print(f"  Discovering via {platform}: {url}")

    html = await fetch_page(url, use_firecrawl_fallback=True)
    if not html:
        print(f"  {platform}: Failed to fetch")
        return events

    events = _extract_events_from_html(html, city_slug, source=f"{platform}_discovery")
    print(f"  {platform}: Found {len(events)} events")

    return events


def _get_ra_co_location(city_slug: str) -> str:
    """Get ra.co location slug."""
    ra_map = {
        "ca--los-angeles": "us/losangeles",
        "ny--new-york": "us/newyorkcity",
        "ca--san-francisco": "us/sanfrancisco",
        "dc--washington": "us/washingtondc",
        "fl--miami": "us/miami",
        "il--chicago": "us/chicago",
        "tx--austin": "us/austin",
        "co--denver": "us/denver",
        "ma--boston": "us/boston",
        "wa--seattle": "us/seattle",
        "tx--houston": "us/houston",
        "ga--atlanta": "us/atlanta",
        "or--portland": "us/portland",
        "nv--las-vegas": "us/lasvegas",
        "pa--philadelphia": "us/philadelphia",
        "mi--detroit": "us/detroit",
        "mn--minneapolis": "us/minneapolis",
        "az--phoenix": "us/phoenix",
        "nc--charlotte": "us/charlotte",
        "tn--nashville": "us/nashville",
        "la--new-orleans": "us/neworleans",
        "ut--salt-lake-city": "us/saltlakecity",
        "nm--albuquerque": "us/albuquerque",
        "va--richmond": "us/richmond",
        "sc--charleston": "us/charleston",
    }
    return ra_map.get(city_slug, "")


def _get_posh_vip_location(city_slug: str) -> str:
    """Get posh.vip location slug."""
    posh_map = {
        "ca--los-angeles": "los-angeles",
        "ca--san-diego": "san-diego",
        "ca--san-francisco": "san-francisco",
        "dc--washington": "washington-dc",
        "fl--miami": "miami",
        "ga--atlanta": "atlanta",
        "il--chicago": "chicago",
        "ny--new-york": "new-york",
        "pa--philadelphia": "philadelphia",
        "tx--austin": "austin",
        "tx--dallas": "dallas",
        "tx--houston": "houston",
        "wa--seattle": "seattle",
        "co--denver": "denver",
        "nv--las-vegas": "las-vegas",
        "ma--boston": "boston",
        "tn--nashville": "nashville",
        "fl--tampa": "tampa",
        "az--phoenix": "phoenix",
        "or--portland": "portland",
    }
    return posh_map.get(city_slug, "")


async def discover_events(
    city_slug: str,
    enable_scira: bool = False,
    enable_firecrawl_search: bool = True,
    enable_platform_discovery: bool = True,
    platforms: List[str] = None,
) -> List[Dict]:
    """
    Main discovery function - finds events from platforms without dedicated scrapers.

    Args:
        city_slug: City identifier (e.g. 'ny--new-york')
        enable_scira: Enable X/Twitter search via Scira API (default OFF)
        enable_firecrawl_search: Enable Google search via Firecrawl
        enable_platform_discovery: Direct platform listing page scraping
        platforms: List of platforms to discover (default: ['partiful', 'ra.co', 'posh.vip'])

    Returns:
        List of event dicts with quality_score field
    """
    if platforms is None:
        platforms = ["partiful", "ra.co", "posh.vip"]

    city_display = _get_city_display_name(city_slug)
    print(f"\n[DISCOVERY] Starting event discovery for {city_display}")
    print(f"  Scira: {'ON' if enable_scira else 'OFF'} | Firecrawl search: {'ON' if enable_firecrawl_search else 'OFF'} | Platform discovery: {'ON' if enable_platform_discovery else 'OFF'}")

    all_events = []

    # 1. Scira X/Twitter search (last, toggled off by default)
    if enable_scira:
        print("  [Scira] Searching X/Twitter...")
        scira_events = await search_with_scira(city_slug)
        all_events.extend(scira_events)
        print(f"  [Scira] Found {len(scira_events)} events")

    # 2. Firecrawl-based Google search for platform links
    if enable_firecrawl_search:
        print("  [Firecrawl] Searching for platform links...")
        search_events = await search_with_firecrawl(city_slug)
        all_events.extend(search_events)
        print(f"  [Firecrawl] Found {len(search_events)} events")

    # 3. Direct platform listing page scraping
    if enable_platform_discovery:
        for platform in platforms:
            try:
                platform_events = await scrape_platform_listing(city_slug, platform)
                all_events.extend(platform_events)
            except Exception as e:
                print(f"  [{platform}] Discovery failed: {e}")

    # Deduplicate by link
    seen_links: Set[str] = set()
    unique_events = []
    for event in all_events:
        link = event.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            unique_events.append(event)

    # Sort by quality score (highest first)
    unique_events.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

    print(f"  [DISCOVERY] Total unique events: {len(unique_events)}")
    return unique_events
