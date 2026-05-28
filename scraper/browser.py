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

                    if data.get('success'):
                        html = data.get('data', {}).get('html', '')
                        if html:
                            return html

                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None

        except Exception as e:
            print(f"Firecrawl attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
    return None


async def fetch_page(url: str, use_firecrawl_fallback: bool = True, skip_playwright: bool = False) -> Optional[str]:
    """
    Fetch page content using Playwright, with Firecrawl/Hyperbrowser fallback
    """
    # Skip playwright and go straight to fallback if requested
    if skip_playwright:
        print("Trying Firecrawl (skip_playwright)...")
        html = await fetch_with_firecrawl(url)
        if html:
            from content_validator import validate_html_content
            is_valid, reason = validate_html_content(html)
            if is_valid:
                print("Firecrawl succeeded (content validated)")
                return html
        return None

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
    """Use Hyperbrowser API (/api/scrape) with captcha solving"""
    if not HYPERBROWSER_API_KEY:
        return None

    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {"url": url, "formats": ["html"]}
                headers = {
                    "x-api-key": HYPERBROWSER_API_KEY,
                    "Content-Type": "application/json",
                }

                async with session.post(
                    "https://api.hyperbrowser.ai/api/scrape",
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
                    job_id = data.get("jobId")
                    if job_id:
                        for poll in range(30):
                            await asyncio.sleep(2)
                            async with session.get(
                                f"https://api.hyperbrowser.ai/api/scrape/{job_id}",
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as status_resp:
                                if status_resp.status != 200:
                                    break
                                status_data = await status_resp.json()
                                if status_data.get("status") == "completed":
                                    html = (
                                        status_data.get("data", {}).get("html", "")
                                        or status_data.get("result", {}).get("html", "")
                                    )
                                    if html:
                                        return html
                                    break
                                elif status_data.get("status") in ("failed", "error"):
                                    break

                    html = data.get('data', {}).get('html', '')
                    if html:
                        return html

                    if attempt < max_retries:
                        await asyncio.sleep(3)
                        continue
                    return None

        except Exception as e:
            print(f"Hyperbrowser attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)
    return None


BROWSERBASE_PROJECT_ID = None

async def _get_browserbase_project_id() -> Optional[str]:
    """Discover Browserbase project ID from API"""
    global BROWSERBASE_PROJECT_ID
    if BROWSERBASE_PROJECT_ID:
        return BROWSERBASE_PROJECT_ID
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.browserbase.com/v1/projects",
                headers={"x-bb-api-key": BROWSERBASE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    projects = await resp.json()
                    if projects and len(projects) > 0:
                        BROWSERBASE_PROJECT_ID = projects[0]["id"]
                        return BROWSERBASE_PROJECT_ID
    except:
        pass
    return None


async def fetch_with_browserbase(url: str, max_retries: int = 1) -> Optional[str]:
    """Use Browserbase remote browser via session + Playwright connect"""
    if not BROWSERBASE_API_KEY:
        return None

    project_id = await _get_browserbase_project_id()
    if not project_id:
        print("Browserbase: Could not discover project ID")
        return None

    for attempt in range(max_retries + 1):
        session_id = None
        try:
            import aiohttp
            from playwright.async_api import async_playwright

            # 1. Create session
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.browserbase.com/v1/sessions",
                    json={"projectId": project_id},
                    headers={"x-bb-api-key": BROWSERBASE_API_KEY, "Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        print(f"Browserbase session creation: {resp.status} {body[:200]}")
                        continue
                    data = await resp.json()
                    connect_url = data.get("connectUrl")
                    session_id = data.get("id")
                    if not connect_url or not session_id:
                        print("Browserbase: No connectUrl in session response")
                        continue

            # 2. Connect via Playwright remote and navigate
            p = await async_playwright().start()
            try:
                browser = await p.chromium.connect(connect_url)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3)
                html = await page.content()
                await browser.close()
                await p.stop()
                if html and len(html.strip()) > 500:
                    return html
            except Exception as e:
                print(f"Browserbase Playwright error: {e}")
                try:
                    await p.stop()
                except:
                    pass

        except Exception as e:
            print(f"Browserbase attempt {attempt+1} failed: {e}")
        finally:
            # 3. Cleanup: delete session
            if session_id:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as s:
                        await s.delete(
                            f"https://api.browserbase.com/v1/sessions/{session_id}",
                            headers={"x-bb-api-key": BROWSERBASE_API_KEY}
                        )
                except:
                    pass
            if attempt < max_retries:
                await asyncio.sleep(3)
    return None


async def fetch_with_anchorbrowser(url: str, max_retries: int = 1) -> Optional[str]:
    """Use Anchorbrowser Web Unlocker API for anti-bot bypass"""
    if not ANCHOR_BROWSER_API_KEY:
        return None

    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {
                    "anchor-api-key": ANCHOR_BROWSER_API_KEY,
                    "Content-Type": "application/json",
                }
                payload = {"url": url}

                async with session.post(
                    "https://api.anchorbrowser.io/v1/tools/fetch/webpage",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        print(f"Anchorbrowser attempt {attempt+1}: status {resp.status}")
                        raw = await resp.text()
                        print(f"  Response: {raw[:300]}")
                        if attempt < max_retries:
                            await asyncio.sleep(3)
                        continue

                    html = await resp.text()
                    if html and len(html.strip()) > 500:
                        return html

                    if attempt < max_retries:
                        await asyncio.sleep(3)
                        continue
                    return None

        except Exception as e:
            print(f"Anchorbrowser attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)
    return None
