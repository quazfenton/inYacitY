#!/usr/bin/env python3
"""
Browser utilities - Playwright primary, Firecrawl fallback, Pydoll last resort
"""

import asyncio
import os
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page

# API Keys
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
HYPERBROWSER_API_KEY = os.environ.get("HYPERBROWSER_API_KEY")
BROWSERBASE_API_KEY = os.environ.get("BROWSERBASE_API_KEY")
ANCHOR_BROWSER_API_KEY = os.environ.get("ANCHOR_BROWSER_API_KEY")


async def create_browser(headless: bool = True) -> Tuple[Browser, Page]:
    """Create Playwright browser with advanced stealth settings"""
    p = await async_playwright().start()
    
    # More comprehensive args to avoid detection
    args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-infobars',
        '--window-size=1920,1080',
        '--window-position=0,0',
        '--force-color-profile=srgb',
        '--disable-extensions',
        '--disable-component-extensions-with-background-pages',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        '--metrics-recording-only',
        '--enable-features=NetworkService,NetworkServiceInProcess',
        '--force-color-profile=srgb',
        '--hide-scrollbars',
    ]
    
    browser = await p.chromium.launch(
        headless=headless,
        args=args
    )
    
    # Create context with realistic settings
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        screen={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/Los_Angeles',
        permissions=['notifications'],
        color_scheme='light',
        reduced_motion='no-preference',
        is_mobile=False,
        has_touch=False,
    )
    
    # Grant permissions
    await context.grant_permissions(['notifications'])
    
    page = await context.new_page()
    
    # Advanced stealth scripts
    await page.add_init_script("""
        // Hide automation
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                {name: 'Native Client', filename: 'internal-nacl-plugin'}
            ]
        });
        
        // Fake chrome
        window.chrome = {
            runtime: {
                OnInstalledReason: {CHROME_UPDATE: "chrome_update"},
                OnRestartRequiredReason: {APP_UPDATE: "app_update"},
                PlatformArch: {X86_64: "x86_64"},
                PlatformNaclArch: {X86_64: "x86_64"},
                PlatformOs: {WIN: "win"},
                RequestUpdateCheckStatus: {NO_UPDATE: "no_update"}
            }
        };
        
        // Fake permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' 
                ? Promise.resolve({state: Notification.permission})
                : originalQuery(parameters)
        );
        
        // Override notification
        window.Notification = window.Notification || {};
        Object.defineProperty(window.Notification, 'permission', {get: () => 'default'});
    """)
    
    # Store playwright instance to prevent garbage collection
    browser._playwright = p
    return browser, page


async def close_browser(browser: Browser):
    """Close browser and cleanup"""
    try:
        await browser.close()
        if hasattr(browser, '_playwright'):
            await browser._playwright.stop()
    except:
        pass


async def fetch_with_firecrawl(url: str, max_retries: int = 2) -> Optional[str]:
    """Fallback: Use Firecrawl API v2 with JS rendering and fresh scrape"""
    if not FIRECRAWL_API_KEY:
        return None

    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}"}
                payload = {
                    "url": url,
                    "formats": ["html"],
                    "onlyMainContent": False,
                    "render": True,
                    "maxAge": 0,
                }

                async with session.post(
                    "https://api.firecrawl.dev/v2/scrape",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        print(f"Firecrawl attempt {attempt+1}: status {resp.status}")
                        if attempt < max_retries:
                            await asyncio.sleep(2 ** attempt)
                        continue

                    data = await resp.json()

                    # v2 response: data is at root level, not nested in 'data'
                    if data.get('success'):
                        html = data.get('html', '')
                        if html:
                            return html

                    # Fallback: search nested keys for HTML content
                    for key in ("html", "content", "page", "body", "scrape", "data"):
                        candidate = data.get(key)
                        if isinstance(candidate, dict):
                            candidate = candidate.get("html") or candidate.get("content")
                        if isinstance(candidate, str) and candidate.strip():
                            return candidate

                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None

        except Exception as e:
            print(f"Firecrawl attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
    return None


async def fetch_page(url: str, use_firecrawl_fallback: bool = True) -> Optional[str]:
    """
    Fetch page content using Playwright, with Firecrawl/Hyperbrowser fallback
    """
    # Try Playwright first
    browser = None
    try:
        print(f"Fetching with Playwright: {url}")
        browser, page = await create_browser(headless=True)
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        html = await page.content()

        # Check if blocked - be more specific to avoid false positives
        html_lower = html.lower()

        # Check for explicit blocked page indicators (full page blocks)
        block_page_indicators = [
            'access denied',
            'captcha required',
            'please complete the security check',
            'verify you are human',
            'human verification',
            'automated access is blocked',
            'bot detected',
            'suspicious activity detected',
            'your ip has been blocked',
            'checking if the site connection is secure',
            'cloudflare',
        ]

        for indicator in block_page_indicators:
            if indicator in html_lower:
                print(f"Playwright: Page appears blocked ({indicator}), will try fallback")
                raise Exception("Blocked")

        # Check for HTTP status codes in error context (not CSS IDs)
        if 'http error 429' in html_lower or 'error 429' in html_lower or 'status 429' in html_lower:
            print("Playwright: Rate limited (429), will try fallback")
            raise Exception("Blocked")

        if 'http error 403' in html_lower or 'error 403' in html_lower or 'status 403' in html_lower:
            print("Playwright: Forbidden (403), will try fallback")
            raise Exception("Blocked")

        if 'http error 401' in html_lower or 'error 401' in html_lower or 'status 401' in html_lower:
            print("Playwright: Unauthorized (401), will try fallback")
            raise Exception("Blocked")

        # Check for empty or near-empty page (another sign of being blocked)
        body_text = await page.inner_text('body')
        if len(body_text.strip()) < 50:
            print(f"Playwright: Page body nearly empty ({len(body_text.strip())} chars), will try fallback")
            raise Exception("Blocked")
        
        await close_browser(browser)
        return html
        
    except Exception as e:
        print(f"Playwright error: {e}")
        if browser:
            await close_browser(browser)
    
    # Try Firecrawl fallback
    if use_firecrawl_fallback:
        print("Trying Firecrawl fallback...")
        html = await fetch_with_firecrawl(url)
        if html:
            from content_validator import validate_html_content
            is_valid, reason = validate_html_content(html)
            if is_valid:
                print("Firecrawl succeeded (content validated)")
                return html
            print(f"Firecrawl returned trash HTML ({reason}), trying next fallback")

        # Try Hyperbrowser as last resort
        print("Trying Hyperbrowser fallback...")
        html = await fetch_with_hyperbrowser(url)
        if html:
            from content_validator import validate_html_content
            is_valid, reason = validate_html_content(html)
            if is_valid:
                print("Hyperbrowser succeeded (content validated)")
                return html
            print(f"Hyperbrowser returned trash HTML ({reason}), trying next fallback")

        # Try Browserbase fallback
        print("Trying Browserbase fallback...")
        html = await fetch_with_browserbase(url)
        if html:
            from content_validator import validate_html_content
            is_valid, reason = validate_html_content(html)
            if is_valid:
                print("Browserbase succeeded (content validated)")
                return html
            print(f"Browserbase returned trash HTML ({reason}), trying next fallback")

        # Try Anchorbrowser fallback
        print("Trying Anchorbrowser fallback...")
        html = await fetch_with_anchorbrowser(url)
        if html:
            from content_validator import validate_html_content
            is_valid, reason = validate_html_content(html)
            if is_valid:
                print("Anchorbrowser succeeded (content validated)")
                return html
            print(f"Anchorbrowser returned trash HTML ({reason})")

    return None


async def fetch_with_hyperbrowser(url: str, max_retries: int = 1) -> Optional[str]:
    """Use Hyperbrowser API v1/browser with captcha solving and full page render"""
    if not HYPERBROWSER_API_KEY:
        return None

    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "url": url,
                    "instructions": "Render the page fully, solve any captchas or Cloudflare challenges, and return the complete HTML.",
                    "solve_captcha": True,
                    "capture": "html",
                }
                headers = {
                    "Authorization": f"Bearer {HYPERBROWSER_API_KEY}",
                    "Content-Type": "application/json",
                }

                async with session.post(
                    "https://api.hyperbrowser.ai/v1/browser",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status != 200:
                        print(f"Hyperbrowser attempt {attempt+1}: status {resp.status}")
                        if attempt < max_retries:
                            await asyncio.sleep(3)
                        continue

                    data = await resp.json()

                    # Search multiple keys since response structure varies
                    for key in ("content", "html", "result", "data"):
                        candidate = data.get(key)
                        if isinstance(candidate, dict):
                            candidate = candidate.get("content") or candidate.get("html")
                        if isinstance(candidate, str) and candidate.strip():
                            return candidate

                    if attempt < max_retries:
                        await asyncio.sleep(3)
                        continue
                    return None

        except Exception as e:
            print(f"Hyperbrowser attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)
    return None


async def fetch_with_browserbase(url: str, max_retries: int = 1) -> Optional[str]:
    """Use Browserbase API for headless browser with stealth and proxy rotation"""
    if not BROWSERBASE_API_KEY:
        return None

    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {BROWSERBASE_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "url": url,
                    "timeout": 45000,
                    "stealth": True,
                    "perform_actions": [
                        {"type": "scroll", "direction": "down", "amount": 2},
                        {"type": "wait", "duration": 2000},
                    ],
                }

                async with session.post(
                    "https://api.browserbase.com/v1/sessions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        print(f"Browserbase attempt {attempt+1}: status {resp.status}")
                        if attempt < max_retries:
                            await asyncio.sleep(3)
                        continue

                    data = await resp.json()

                    # Browserbase returns HTML in various keys depending on endpoint
                    for key in ("html", "content", "dom", "page", "data"):
                        candidate = data.get(key)
                        if isinstance(candidate, dict):
                            candidate = candidate.get("html") or candidate.get("content")
                        if isinstance(candidate, str) and candidate.strip():
                            return candidate

                    # Check nested session structure
                    session_data = data.get("session") or data.get("data")
                    if isinstance(session_data, dict):
                        for key in ("html", "content", "dom"):
                            candidate = session_data.get(key)
                            if isinstance(candidate, str) and candidate.strip():
                                return candidate

                    if attempt < max_retries:
                        await asyncio.sleep(3)
                        continue
                    return None

        except Exception as e:
            print(f"Browserbase attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)
    return None


async def fetch_with_anchorbrowser(url: str, max_retries: int = 1) -> Optional[str]:
    """Use Anchorbrowser API for anti-bot bypass with CAPTCHA solving"""
    if not ANCHOR_BROWSER_API_KEY:
        return None

    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {ANCHOR_BROWSER_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "url": url,
                    "wait": "networkidle",
                    "timeout": 60,
                    "bypass_cloudflare": True,
                    "solve_captcha": True,
                }

                async with session.post(
                    "https://api.anchorbrowser.io/v1/page",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        print(f"Anchorbrowser attempt {attempt+1}: status {resp.status}")
                        if attempt < max_retries:
                            await asyncio.sleep(3)
                        continue

                    data = await resp.json()

                    # Anchorbrowser returns content in various keys
                    for key in ("content", "html", "result", "data", "page"):
                        candidate = data.get(key)
                        if isinstance(candidate, dict):
                            candidate = candidate.get("content") or candidate.get("html")
                        if isinstance(candidate, str) and candidate.strip():
                            return candidate

                    # Check nested structure
                    nested = data.get("data") or data.get("page") or data.get("browser")
                    if isinstance(nested, dict):
                        for key in ("content", "html"):
                            candidate = nested.get(key)
                            if isinstance(candidate, str) and candidate.strip():
                                return candidate

                    if attempt < max_retries:
                        await asyncio.sleep(3)
                        continue
                    return None

        except Exception as e:
            print(f"Anchorbrowser attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)
    return None
