#!/usr/bin/env python3
"""
Browser utilities - Playwright primary, Firecrawl fallback, Pydoll last resort
"""

import asyncio
import os
import platform
import re
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
from config_loader import get_config

# API Keys
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
HYPERBROWSER_API_KEY = os.environ.get("HYPERBROWSER_API_KEY")
BROWSERBASE_API_KEY = os.environ.get("BROWSERBASE_API_KEY")
ANCHOR_BROWSER_API_KEY = os.environ.get("ANCHOR_BROWSER_API_KEY")

# Platform helpers
IS_WINDOWS = platform.system() == "Windows"


def chromium_args() -> list:
    """Common Chromium args, excluding --no-sandbox on Windows."""
    args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-gpu',
    ]
    if not IS_WINDOWS:
        args.append('--no-sandbox')
    return args


async def dismiss_overlays(tab) -> None:
    """Try multiple strategies to dismiss dialogs/overlays on a pydoll Tab.
    Saves/restores URL to prevent accidental navigation from close-button clicks.
    Runs multiple passes to catch re-rendered overlays."""
    import json

    url_before = None
    try:
        url_before = await tab.current_url
    except Exception:
        pass

    for _pass in range(3):
        scripts = [
            # 1: Escape key dispatch (handles many Facebook modals)
            """document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27, which: 27, bubbles: true}));""",
            # 2: Find and click close buttons — only aria-label Close/Dismiss (safe, no redirect)
            """(function() {
                const selectors = [
                    '[aria-label="Close"]', '[aria-label="Dismiss"]',
                    '[aria-label="close"]', '[aria-label="dismiss"]',
                    'div[role="dialog"] [aria-label="Close"]',
                    'div[role="dialog"] [aria-label="close"]',
                    'div[aria-label="Close"][role="button"]',
                    'div[aria-label="close"][role="button"]',
                    'div[role="dialog"] div[aria-label="Close"]',
                    'div[role="dialog"] div[aria-label="close"]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) { el.click(); return true; }
                }
                return false;
            })()""",
            # 3: Remove overlay elements completely (safe, removes from DOM, no navigation)
            """(function() {
                const overlays = document.querySelectorAll(
                    'div[role="dialog"], div[role="presentation"][aria-hidden], ' +
                    'div[data-pagelet*="modal"]'
                );
                let count = 0;
                overlays.forEach(el => {
                    if (el.offsetParent !== null) { el.remove(); count++; }
                });
                document.body.style.overflow = '';
                document.body.style.position = '';
                document.documentElement.style.overflow = '';
                return count;
            })()""",
            # 4: Remove fixed-position viewport-covering elements
            """(function() {
                let count = 0;
                document.querySelectorAll('div').forEach(el => {
                    try {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed' && el.offsetParent !== null) {
                            const rect = el.getBoundingClientRect();
                            const vw = window.innerWidth;
                            const vh = window.innerHeight;
                            if (rect.top <= 10 && rect.left <= 10 &&
                                rect.bottom >= vh - 10 && rect.right >= vw - 10) {
                                el.remove(); count++;
                            }
                        }
                    } catch(e) {}
                });
                return count;
            })()""",
        ]
        for script in scripts:
            try:
                await tab.execute_script(script)
            except Exception:
                pass
        await asyncio.sleep(1)

    # Restore URL if we accidentally navigated away
    if url_before:
        try:
            url_after = await tab.current_url
            if url_after != url_before:
                print(f"  [dismiss] Navigated away! Restoring URL...")
                await tab.go_to(url_before)
                await asyncio.sleep(2)
        except Exception:
            pass


async def scroll_page(tab, max_scrolls: int = 15, scroll_pause: float = 2.0, scroll_attempts_before_stop: int = 3) -> int:
    """Scroll a pydoll page to trigger infinite-load content.
    
    Args:
        tab: pydoll Tab object
        max_scrolls: Maximum number of scroll operations
        scroll_pause: Seconds to wait between scrolls for content to load
        scroll_attempts_before_stop: How many consecutive scrolls with no height change before stopping
    
    Returns:
        Number of scrolls performed
    """
    try:
        last_height = await tab.execute_script("return document.body.scrollHeight")
    except Exception:
        return 0
    
    no_change_count = 0
    scrolls_done = 0
    
    for i in range(max_scrolls):
        # Scroll to bottom
        try:
            await tab.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            break
        
        await asyncio.sleep(scroll_pause)
        
        # Check if height changed (new content loaded)
        try:
            new_height = await tab.execute_script("return document.body.scrollHeight")
        except Exception:
            break
        
        if new_height > last_height:
            no_change_count = 0
            last_height = new_height
            scrolls_done += 1
        else:
            no_change_count += 1
            if no_change_count >= scroll_attempts_before_stop:
                break
    
    if scrolls_done > 0:
        print(f"  [scroll] Performed {scrolls_done} scrolls, final height {last_height}")
    return scrolls_done


def _is_cloudflare_page(html: str) -> bool:
    """Check if HTML is a Cloudflare challenge/interstitial page (not real content)."""
    if len(html.strip()) > 50000:
        return False  # too large to be a challenge page
    lower = html.lower()
    challenge_signals = [
        'attention required', 'cloudflare', 'checking your browser',
        'please complete the security check', 'verify you are human',
        'just a moment', 'cf-browser-verification',
        'cf_challenge_response', 'cdn-cgi/challenge-platform',
        'turnstile',
    ]
    return any(s in lower for s in challenge_signals) and 'id="facebook"' not in html


def _is_login_page(html: str) -> bool:
    """Check if HTML is a Facebook login wall (not actual content)."""
    lower = html.lower()
    login_signals = [
        'login', 'log in', 'sign in', 'create new account',
        'enter your email', 'enter your password',
        'keep me logged in', 'forgot password',
    ]
    login_count = sum(1 for s in login_signals if s in lower)
    # If more than 2 login signals AND lacks event content structure
    return login_count >= 2 and 'href="/events/' not in html


def _has_event_content(html: str) -> bool:
    """Check if HTML contains actual Facebook event listings."""
    lower = html.lower()
    # Event links are the most reliable signal
    if 'href="/events/' in lower:
        return True
    # Check for event-specific pagelet containers
    if 'data-pagelet="event' in lower:
        return True
    # Check for event-related JSON data
    if 'application/ld+json' in lower and '"name"' in lower and '"startdate"' in lower:
        return True
    return False


def _get_cookie_file() -> str:
    """Get cookie file path from config (empty string = disabled)."""
    config = get_config()
    return config.get('BROWSER', {}).get('COOKIE_FILE', '') or ''


async def inject_cookies_playwright(context, cookie_file: str = None) -> bool:
    """Load cookies from a JSON file into a Playwright browser context.
    File format: list of dicts with keys: name, value, domain, path, httpOnly, secure, sameSite, expires.
    Return True on success."""
    if cookie_file is None:
        cookie_file = _get_cookie_file()
    if not cookie_file or not os.path.isfile(cookie_file):
        return False
    try:
        import json
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        if not isinstance(cookies, list):
            cookies = [cookies]
        valid = []
        for c in cookies:
            if c.get('name') and c.get('value') and c.get('domain'):
                valid.append({
                    'name': c['name'],
                    'value': c['value'],
                    'domain': c['domain'],
                    'path': c.get('path', '/'),
                    'httpOnly': c.get('httpOnly', False),
                    'secure': c.get('secure', True),
                    'sameSite': c.get('sameSite', 'Lax'),
                })
        if valid:
            await context.add_cookies(valid)
            print(f"  [Cookies] Loaded {len(valid)} cookies from {cookie_file}")
            return True
    except Exception as e:
        print(f"  [Cookies] Error loading {cookie_file}: {e}")
    return False


async def inject_cookies_pydoll(page, cookie_file: str = None) -> bool:
    """Load cookies from a JSON file into a pydoll page.
    File format: list of dicts with keys: name, value, domain, path, httpOnly, secure, sameSite.
    Return True on success."""
    if cookie_file is None:
        cookie_file = _get_cookie_file()
    if not cookie_file or not os.path.isfile(cookie_file):
        return False
    try:
        import json
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        if not isinstance(cookies, list):
            cookies = [cookies]
        valid = []
        for c in cookies:
            if c.get('name') and c.get('value') and c.get('domain'):
                valid.append({
                    'name': c['name'],
                    'value': c['value'],
                    'domain': c['domain'],
                    'path': c.get('path', '/'),
                    'httpOnly': c.get('httpOnly', False),
                    'secure': c.get('secure', True),
                    'sameSite': c.get('sameSite', 'Lax'),
                })
        if valid:
            await page.set_cookies(valid)
            print(f"  [Cookies] Loaded {len(valid)} cookies from {cookie_file}")
            return True
    except Exception as e:
        print(f"  [Cookies] Error loading {cookie_file}: {e}")
    return False


# Device profiles for rotating fingerprints to evade detection
BROWSER_PROFILES = {
    'desktop_win': {
        'viewport': {'width': 1920, 'height': 1080},
        'screen': {'width': 1920, 'height': 1080},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'locale': 'en-US',
        'timezone_id': 'America/New_York',
        'is_mobile': False,
        'has_touch': False,
    },
    'desktop_mac': {
        'viewport': {'width': 1512, 'height': 982},
        'screen': {'width': 1512, 'height': 982},
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'locale': 'en-US',
        'timezone_id': 'America/Los_Angeles',
        'is_mobile': False,
        'has_touch': False,
    },
    'mobile_iphone': {
        'viewport': {'width': 390, 'height': 844},
        'screen': {'width': 390, 'height': 844},
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'locale': 'en-US',
        'timezone_id': 'America/New_York',
        'is_mobile': True,
        'has_touch': True,
    },
    'mobile_android': {
        'viewport': {'width': 412, 'height': 915},
        'screen': {'width': 412, 'height': 915},
        'user_agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
        'locale': 'en-US',
        'timezone_id': 'America/Chicago',
        'is_mobile': True,
        'has_touch': True,
    },
}

PROFILE_ORDER = ['desktop_win', 'desktop_mac', 'mobile_iphone', 'mobile_android']


async def create_browser(headless: bool = True, profile_name: str = None) -> Tuple[Browser, Page]:
    """Create Playwright browser with advanced stealth settings.
    
    Args:
        headless: Run headless
        profile_name: Device profile to use (None = random)
    """
    p = await async_playwright().start()
    
    # Pick profile
    if profile_name is None or profile_name not in BROWSER_PROFILES:
        import random
        profile_name = random.choice(PROFILE_ORDER)
    profile = BROWSER_PROFILES[profile_name]
    
    # More comprehensive args to avoid detection
    win_size = f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}'
    args = chromium_args() + [
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-infobars',
        win_size,
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
        '--hide-scrollbars',
        '--ignore-certificate-errors',
    ]
    
    browser = await p.chromium.launch(
        headless=headless,
        args=args
    )
    
    # Create context with realistic settings from profile
    context = await browser.new_context(
        ignore_https_errors=True,
        viewport=profile['viewport'],
        screen=profile['screen'],
        user_agent=profile['user_agent'],
        locale=profile['locale'],
        timezone_id=profile['timezone_id'],
        permissions=['notifications'],
        color_scheme='light',
        reduced_motion='no-preference',
        is_mobile=profile['is_mobile'],
        has_touch=profile['has_touch'],
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
        
        # Inject cookies if configured
        await inject_cookies_playwright(page.context)
        
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

    # Retry Playwright with different device profiles (mobile often evades desktop-targeted blocking)
    for retry_profile in ['mobile_iphone', 'mobile_android', 'desktop_mac']:
        print(f"Retrying Playwright with profile '{retry_profile}'...")
        p_browser = None
        try:
            p_browser, page = await create_browser(headless=True, profile_name=retry_profile)
            # Inject cookies if configured
            await inject_cookies_playwright(page.context)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            html = await page.content()
            html_lower = html.lower()
            blocked = any(ind in html_lower for ind in [
                'access denied', 'captcha required', 'please complete the security check',
                'verify you are human', 'cloudflare', 'checking if the site connection is secure',
                'automated access is blocked', 'bot detected', 'suspicious activity detected',
            ])
            if not blocked:
                body_text = await page.inner_text('body')
                if len(body_text.strip()) >= 50:
                    print(f"Playwright ({retry_profile}) succeeded")
                    await close_browser(p_browser)
                    return html
            print(f"Playwright ({retry_profile}): blocked")
            await close_browser(p_browser)
        except Exception as e2:
            print(f"Playwright ({retry_profile}): {e2}")
            if p_browser:
                await close_browser(p_browser)

    # Try paid API fallbacks
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

    # Try undetected browsers last, only if config allows
    config = get_config()
    if config.get('BROWSER.STEALTH_ENABLED', False):
        # Method 1: pydoll directly (has built-in Cloudflare auto-solve)
        try:
            from pydoll.browser import Chrome as PydollChrome
            from pydoll.browser.options import ChromiumOptions

            print("Trying pydoll (Cloudflare bypass)...")
            options = ChromiumOptions()
            for arg in chromium_args():
                options.add_argument(arg)
            options.headless = True
            options.start_timeout = 30
            p_browser = PydollChrome(options=options)
            page = await p_browser.start()
            await page.enable_auto_solve_cloudflare_captcha()

            # Inject cookies before navigation if configured
            await inject_cookies_pydoll(page)

            await page.go_to(url)
            await asyncio.sleep(5)

            # Track the best HTML across attempts — event data may exist
            # under the login overlay even before dismissal
            best_html = None

            for attempt in range(3):
                # Grab raw HTML BEFORE dismissal — events may be in DOM underneath overlay
                if attempt == 0:
                    raw_html = await page.page_source
                    if len(raw_html.strip()) > len((best_html or '').strip()):
                        best_html = raw_html

                await dismiss_overlays(page)
                await asyncio.sleep(1)

                # Scroll to trigger infinite-load content (more events)
                await scroll_page(page, max_scrolls=15, scroll_pause=2.0)

                html = await page.page_source

                # Keep the largest HTML (most content-rich)
                if len(html.strip()) > len((best_html or '').strip()):
                    best_html = html

                # If we found good content, return immediately
                if _has_event_content(html):
                    print(f"pydoll succeeded (attempt {attempt+1}, {len(html.strip())} chars)")
                    await p_browser.stop()
                    return html

                # Check explicitly for Cloudflare (real block, not login wall)
                if _is_cloudflare_page(html):
                    print(f"pydoll attempt {attempt+1}: Cloudflare challenge, refreshing...")
                    await page.go_to(url)
                    await asyncio.sleep(5)
                    continue

                # Login wall or no content — refresh since popup won't reappear
                if attempt < 2:
                    print(f"pydoll attempt {attempt+1}: still blocked or no events, refreshing...")
                    await page.go_to(url)
                    await asyncio.sleep(5)

            # Return best HTML even if login wall persists — parser may find
            # event data hidden under the overlay
            if best_html and len(best_html.strip()) > 500:
                if _is_login_page(best_html):
                    print(f"pydoll: login wall persisted, returning best HTML ({len(best_html.strip())} chars) for parser to try")
                else:
                    print(f"pydoll: returning best HTML ({len(best_html.strip())} chars)")
                await p_browser.stop()
                return best_html

            print(f"pydoll: no usable HTML returned")
            await p_browser.stop()
        except ImportError:
            print("  pydoll not installed")
        except Exception as e:
            print(f"  pydoll failed: {e}")

        # Method 2: consent_handler.create_undetected_browser fallback
        try:
            from consent_handler import create_undetected_browser, close_undetected_browser

            print("Trying undetected browser (patchright/playwright)...")
            p_browser, page, browser_type = await create_undetected_browser(
                use_pydoll=False,  # already tried above
                use_patchright=True,
                use_botright=False,
                headless=True,
            )
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)
                html = await page.content()
                html_lower = html.lower()
                blocked = any(ind in html_lower for ind in [
                    'access denied', 'captcha required', 'verify you are human',
                    'please complete the security check', 'cloudflare',
                    'checking if the site connection is secure',
                ])
                if not blocked and len(html.strip()) > 200:
                    print(f"Undetected browser ({browser_type}) succeeded")
                    await close_undetected_browser(p_browser, browser_type)
                    return html
                print(f"Undetected browser ({browser_type}): page blocked or empty")
            finally:
                await close_undetected_browser(p_browser, browser_type)
        except ImportError:
            print("  consent_handler not available")
        except Exception as e:
            print(f"  Undetected browser fallback failed: {e}")

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
