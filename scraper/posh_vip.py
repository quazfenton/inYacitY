#!/usr/bin/env python3
"""
Posh.vip Event Scraper - Fixed with aiohttp primary
"""

import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import aiohttp


POSH_VIP_CITY_MAP = {
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
}


async def fetch_with_aiohttp(url: str) -> Optional[str]:
    """Fetch page using aiohttp with browser-like headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30, ssl=False) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    print(f"HTTP {resp.status}")
    except Exception as e:
        print(f"aiohttp error: {e}")
    return None


def build_posh_vip_url(city_code: str) -> Optional[str]:
    """Build posh.vip URL for a city"""
    if city_code not in POSH_VIP_CITY_MAP:
        return None
    return f"https://posh.vip/events/{POSH_VIP_CITY_MAP[city_code]}"


def clean_posh_description(text: str) -> str:
    """Clean description and append '...' if truncated."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    # If description is long, truncate and add ...
    if len(text) > 300:
        text = text[:300]
        if not text.endswith(('.', '!', '?', '"', "'", '...')):
            text = text + "..."
    return text


async def scrape_posh_vip(city: str = "ca--los-angeles") -> list:
    """Scrape Posh.vip events"""
    # Check if city is supported
    if city not in POSH_VIP_CITY_MAP:
        print(f"⚠ Posh.vip: City '{city}' not supported. Skipping.")
        return []
    
    url = build_posh_vip_url(city)
    if not url:
        return []
    
    output_file = os.path.join(os.path.dirname(__file__), "posh_vip_events.json")
    
    print(f"\nScraping Posh.vip: {url}")
    
    html = await fetch_with_aiohttp(url)
    if not html:
        print("Failed to fetch Posh.vip page")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # Look for event cards - posh.vip uses React components
    # Try multiple selectors
    cards = soup.find_all('a', href=re.compile(r'/e/'))
    
    for card in cards:
        try:
            href = card.get('href', '')
            if not href:
                continue
                
            if href.startswith('/'):
                href = f"https://posh.vip{href}"
            
            # Extract title
            title = None
            title_elem = card.find(['h2', 'h3', 'h4', 'p', 'span', 'div'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            if not title:
                title = card.get('aria-label', '')
            
            # Skip if it looks like a nav link
            if title and len(title) > 3 and 'posh' not in title.lower():
                events.append({
                    'title': title,
                    'link': href,
                    'date': 'TBA',
                    'time': 'TBA',
                    'location': 'TBA',
                    'description': '',
                    'source': 'Posh.vip',
                    'city': city
                })
        except Exception as e:
            continue
    
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

    out_data['cities'][city] = {
        'events': events,
        'total': len(events),
        'last_updated': datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(out_data, f, indent=2)
    
    print(f"✓ Saved {len(events)} events to {output_file}")
    return events


async def main():
    events = await scrape_posh_vip("ca--los-angeles")
    print(f"Found {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['link'][:50]}")


if __name__ == '__main__':
    asyncio.run(main())