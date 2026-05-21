#!/usr/bin/env python3
"""
Proxy Fallback Module - Prewarmed public free proxy list for last-resort retries.

Usage: ONLY called AFTER all current methods (Playwright + all API fallbacks)
return 0 events or a definitive 404. Never intercepts or skips existing flows.

Proxy sources (public, free, updated):
  - github.com/proxifly/free-proxy-list
  - github.com/TheSpeedX/SOCKS-List
  - github.com/ShiftyTR/Proxy-List

Config toggle: PROXY_FALLBACK.ENABLED (default: false)
"""

import asyncio
import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

PROXY_CACHE_FILE = Path(__file__).parent / "proxy_cache.json"
PROXY_CACHE_TTL_SECONDS = 3600  # Refresh proxy list every hour

# Public GitHub sources for free proxy lists
PROXY_SOURCES = [
    {
        "url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
        "type": "http",
    },
    {
        "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "type": "http",
    },
    {
        "url": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "type": "http",
    },
    {
        "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "type": "socks5",
    },
]


def _load_proxy_cache() -> Dict:
    """Load cached proxy list if still valid."""
    if PROXY_CACHE_FILE.exists():
        try:
            with open(PROXY_CACHE_FILE, "r") as f:
                cache = json.load(f)
            cached_at = datetime.fromisoformat(cache.get("cached_at", ""))
            if datetime.now() - cached_at < timedelta(seconds=PROXY_CACHE_TTL_SECONDS):
                return cache
        except (json.JSONDecodeError, ValueError, IOError):
            pass
    return {"proxies": [], "cached_at": None, "validated": []}


def _save_proxy_cache(cache: Dict):
    """Save proxy list to cache."""
    cache["cached_at"] = datetime.now().isoformat()
    PROXY_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROXY_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


async def _fetch_proxy_list() -> List[str]:
    """Fetch proxy lists from all GitHub sources."""
    all_proxies: List[str] = []

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for source in PROXY_SOURCES:
                try:
                    async with session.get(
                        source["url"],
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            lines = [
                                line.strip()
                                for line in text.strip().split("\n")
                                if line.strip() and ":" in line
                            ]
                            all_proxies.extend(lines)
                            print(f"  [Proxy] Fetched {len(lines)} from {source['url'].split('/')[-1]}")
                except Exception as e:
                    print(f"  [Proxy] Failed to fetch {source['url'].split('/')[-1]}: {e}")

                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"  [Proxy] Failed to fetch proxy lists: {e}")

    # Deduplicate
    return list(dict.fromkeys(all_proxies))


async def _validate_proxy(proxy: str, test_url: str = "https://httpbin.org/ip", timeout: int = 8) -> bool:
    """Test if a proxy is working."""
    try:
        import aiohttp

        proxy_type = "socks5" if proxy.startswith("socks") else "http"
        proxy_url = f"{proxy_type}://{proxy}" if not proxy.startswith("http") and not proxy.startswith("socks") else proxy

        connector = aiohttp.TCPConnector(limit=1)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                test_url,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                return resp.status == 200

    except Exception:
        return False


async def validate_proxies(proxies: List[str], max_concurrent: int = 10, max_valid: int = 15) -> List[str]:
    """Validate proxies concurrently, stop after finding enough working ones."""
    if not proxies:
        return []

    print(f"  [Proxy] Validating {len(proxies)} proxies (need {max_valid} working)...")

    semaphore = asyncio.Semaphore(max_concurrent)
    working: List[str] = []
    stop_event = asyncio.Event()

    async def _check(proxy: str):
        if stop_event.is_set():
            return
        async with semaphore:
            if stop_event.is_set():
                return
            is_valid = await _validate_proxy(proxy)
            if is_valid:
                working.append(proxy)
                if len(working) >= max_valid:
                    stop_event.set()

    tasks = [asyncio.create_task(_check(p)) for p in proxies]
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"  [Proxy] Found {len(working)} working proxies")
    return working[:max_valid]


async def get_prewarmed_proxies(force_refresh: bool = False) -> List[str]:
    """
    Get prewarmed, validated proxy list.
    Fetches from GitHub sources if cache is stale or empty.
    """
    cache = _load_proxy_cache()

    if not force_refresh and cache.get("validated"):
        print(f"  [Proxy] Using {len(cache['validated'])} cached validated proxies")
        return cache["validated"]

    # Fetch fresh proxy list
    print("  [Proxy] Fetching fresh proxy list from GitHub sources...")
    raw_proxies = await _fetch_proxy_list()

    if not raw_proxies:
        print("  [Proxy] No proxies fetched, returning empty list")
        return []

    # Validate
    validated = await validate_proxies(raw_proxies)

    # Cache results
    _save_proxy_cache({"proxies": raw_proxies, "validated": validated})

    return validated


async def fetch_with_proxy(url: str, proxy: str, timeout: int = 30) -> Optional[str]:
    """
    Fetch a URL using a specific proxy via Playwright.
    Does NOT modify any existing fetch_page implementation.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context = await browser.new_context(
                proxy={"server": proxy},
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                await asyncio.sleep(2)
                html = await page.content()
                await browser.close()
                return html
            except Exception:
                await browser.close()
                return None

    except Exception as e:
        print(f"    [Proxy] fetch_with_proxy failed for {proxy}: {e}")
        return None


async def retry_with_proxies(
    url: str,
    max_retries: int = 3,
    force_refresh_proxies: bool = False,
) -> Optional[str]:
    """
    Retry fetching a URL using rotating proxies.
    Only call this AFTER all existing methods have failed.
    """
    proxies = await get_prewarmed_proxies(force_refresh=force_refresh_proxies)

    if not proxies:
        print("  [Proxy] No working proxies available")
        return None

    print(f"  [Proxy] Retrying {url} with {max_retries} proxy attempts...")

    # Shuffle to distribute load
    random.shuffle(proxies)

    for i, proxy in enumerate(proxies[:max_retries]):
        print(f"    [Proxy] Attempt {i+1}/{max_retries} via {proxy}")
        html = await fetch_with_proxy(url, proxy)

        if html and len(html.strip()) > 100:
            print(f"    [Proxy] Success via {proxy}")
            return html

        await asyncio.sleep(1)

    print("  [Proxy] All proxy attempts failed")
    return None


async def scrape_with_proxy_fallback(
    url: str,
    parse_fn,
    max_proxy_retries: int = 3,
) -> List[Dict]:
    """
    High-level helper: if parse_fn returns 0 events, retry with proxies.

    Usage in a scraper:
        events = await scrape_with_proxy_fallback(
            url=url,
            parse_fn=lambda html: parse_events_from_html(html),
            max_proxy_retries=3,
        )

    This is completely additive - parse_fn is called normally first,
    proxies only used if it returns empty.
    """
    # Normal flow already happened before calling this.
    # This function is the additive retry layer.
    html = await retry_with_proxies(url, max_retries=max_proxy_retries)

    if not html:
        return []

    try:
        return parse_fn(html)
    except Exception as e:
        print(f"  [Proxy] Parse failed after proxy fetch: {e}")
        return []
