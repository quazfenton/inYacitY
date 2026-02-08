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


async def fetch_with_firecrawl(url: str) -> Optional[str]:
    """Fallback: Use Firecrawl API to fetch page content"""
    if not FIRECRAWL_API_KEY:
        return None
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}"}
            payload = {"url": url, "formats": ["html"], "onlyMainContent": False}
            
            async with session.post(
                "https://api.firecrawl.dev/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('success') and 'data' in data:
                        return data['data'].get('html', '')
    except Exception as e:
        print(f"Firecrawl failed: {e}")
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
            print("Firecrawl succeeded")
            return html
        print("Firecrawl failed")
        
        # Try Hyperbrowser as last resort
        print("Trying Hyperbrowser fallback...")
        html = await fetch_with_hyperbrowser(url)
        if html:
            print("Hyperbrowser succeeded")
            return html
        print("Hyperbrowser failed")
    
    return None


async def fetch_with_hyperbrowser(url: str) -> Optional[str]:
    """Use Hyperbrowser API to fetch page content"""
    if not HYPERBROWSER_API_KEY:
        return None
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {HYPERBROWSER_API_KEY}"}
            payload = {
                "url": url,
                "session_options": {
                    "accept_cookies": True,
                    "solve_captchas": True
                }
            }
            
            async with session.post(
                "https://api.hyperbrowser.ai/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=90)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data', {}).get('html', '')
                else:
                    print(f"Hyperbrowser status: {resp.status}")
    except Exception as e:
        print(f"Hyperbrowser error: {e}")
    return None
