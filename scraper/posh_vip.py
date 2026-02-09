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


async def scrape_posh_vip(city: str = "ca--los-angeles") -> list:
    """Scrape Posh.vip events"""
    url = build_posh_vip_url(city)
    if not url:
        print(f"City {city} not supported")
        return []
    
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
                    'source': 'Posh.vip'
                })
        except Exception as e:
            continue
    
    return events


async def main():
    events = await scrape_posh_vip("ca--los-angeles")
    print(f"Found {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title'][:50]} | {e['link'][:50]}")


if __name__ == '__main__':
    asyncio.run(main())