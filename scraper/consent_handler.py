#!/usr/bin/env python3
"""
Module to handle consent screens and blocking elements during web scraping
Enhanced with pydoll, Patchright, and advanced anti-detection
Implements real browser profiles and fingerprint consistency
"""

import asyncio
import json
import os
import random
import re
import time
from typing import Dict, Optional, List, Tuple
import base64
import hashlib
import functools
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
import aiohttp

# Try to import enhanced browser engines
PYDOLL_AVAILABLE = False
PATCHRIGHT_AVAILABLE = False
BOTRIGHT_AVAILABLE = False

try:
    from pydoll.browser import Chrome as PydollChrome
    from pydoll.constants import By
    from pydoll.browser.options import ChromiumOptions
    PYDOLL_AVAILABLE = True
    print("✅ pydoll available - Cloudflare bypass enabled")
except ImportError:
    print("⚠️  pydoll not available - install with: pip install pydoll")

try:
    import patchright.async_api as patchright
    PATCHRIGHT_AVAILABLE = True
    print("✅ Patchright available - Enhanced stealth mode enabled")
except ImportError:
    print("⚠️  Patchright not available - install with: pip install patchright")

try:
    import botright
    BOTRIGHT_AVAILABLE = True
    print("✅ Botright available - Advanced anti-detection enabled")
except ImportError:
    print("⚠️  Botright not available - install with: pip install botright")


# Pydoll Retry Decorator
def pydoll_retry(max_retries=3, delay=2.0, backoff=2.0, exceptions=(Exception,)):
    """
    Retry decorator for pydoll operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        print(f"❌ {func.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    print(f"⚠️  {func.__name__} attempt {attempt + 1} failed: {e}")
                    print(f"   Retrying in {current_delay:.1f} seconds...")
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                    
                    # Add some jitter to avoid thundering herd
                    jitter = random.uniform(0.1, 0.5)
                    await asyncio.sleep(jitter)
            
            raise last_exception
        return wrapper
    return decorator


# Enhanced error recovery for browser operations
class BrowserRecoveryManager:
    """Manages browser recovery strategies and fallback mechanisms"""
    
    def __init__(self):
        self.recovery_strategies = [
            self._restart_browser,
            self._clear_cache_and_retry,
            self._change_user_agent,
            self._use_different_profile,
            self._add_random_delay,
        ]
    
    async def _restart_browser(self, browser, browser_type, **kwargs):
        """Restart the browser completely"""
        print("🔄 Recovery strategy: Restarting browser...")
        try:
            await close_undetected_browser(browser, browser_type)
            await asyncio.sleep(random.uniform(2.0, 5.0))
            return await create_undetected_browser(**kwargs)
        except Exception as e:
            print(f"   Browser restart failed: {e}")
            raise
    
    async def _clear_cache_and_retry(self, browser, browser_type, **kwargs):
        """Clear browser cache and cookies"""
        print("🧹 Recovery strategy: Clearing cache...")
        try:
            if browser_type == 'pydoll':
                # For pydoll, we need to restart as cache clearing isn't directly available
                return await self._restart_browser(browser, browser_type, **kwargs)
            else:
                # For Playwright-based browsers
                context = browser.contexts[0] if browser.contexts else None
                if context:
                    await context.clear_cookies()
                    await context.clear_permissions()
                return browser, browser.contexts[0].pages[0] if context and context.pages else None, browser_type
        except Exception as e:
            print(f"   Cache clearing failed: {e}")
            raise
    
    async def _change_user_agent(self, browser, browser_type, **kwargs):
        """Change user agent and retry"""
        print("🎭 Recovery strategy: Changing user agent...")
        # This requires restarting with a different profile
        return await self._restart_browser(browser, browser_type, **kwargs)
    
    async def _use_different_profile(self, browser, browser_type, **kwargs):
        """Use a different browser profile"""
        print("👤 Recovery strategy: Using different profile...")
        # Select a different profile
        profiles = list(REAL_BROWSER_PROFILES.keys())
        current_profile = kwargs.get('profile_name')
        if current_profile in profiles:
            profiles.remove(current_profile)
        
        if profiles:
            kwargs['profile_name'] = random.choice(profiles)
        
        return await self._restart_browser(browser, browser_type, **kwargs)
    
    async def _add_random_delay(self, browser, browser_type, **kwargs):
        """Add random delay and continue"""
        print("⏱️  Recovery strategy: Adding random delay...")
        delay = random.uniform(5.0, 15.0)
        await asyncio.sleep(delay)
        return browser, None, browser_type  # Return existing browser
    
    async def attempt_recovery(self, browser, browser_type, error, strategy_index=0, **kwargs):
        """Attempt recovery using available strategies"""
        if strategy_index >= len(self.recovery_strategies):
            print("❌ All recovery strategies exhausted")
            raise error
        
        try:
            strategy = self.recovery_strategies[strategy_index]
            return await strategy(browser, browser_type, **kwargs)
        except Exception as recovery_error:
            print(f"   Recovery strategy {strategy_index + 1} failed: {recovery_error}")
            return await self.attempt_recovery(browser, browser_type, error, strategy_index + 1, **kwargs)


# Global recovery manager instance
recovery_manager = BrowserRecoveryManager()


# Real browser profiles captured from actual browsers
REAL_BROWSER_PROFILES = {
    'windows_chrome_120': {
        'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'platform': 'Win32',
        'hardwareConcurrency': 8,
        'deviceMemory': 8,
        'maxTouchPoints': 0,
        'vendor': 'Google Inc.',
        'language': 'en-US',
        'languages': ['en-US', 'en'],
        'timezone': 'America/New_York',
        'screen': {
            'width': 1920,
            'height': 1080,
            'availWidth': 1920,
            'availHeight': 1040,
            'colorDepth': 24,
            'pixelDepth': 24,
        },
        'viewport': {
            'width': 1920,
            'height': 1080,
        },
        'webgl': {
            'vendor': 'Google Inc. (NVIDIA)',
            'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)',
        },
    },
    'windows_chrome_131': {
        'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'platform': 'Win32',
        'hardwareConcurrency': 16,
        'deviceMemory': 8,
        'maxTouchPoints': 0,
        'vendor': 'Google Inc.',
        'language': 'en-US',
        'languages': ['en-US', 'en'],
        'timezone': 'America/Los_Angeles',
        'screen': {
            'width': 2560,
            'height': 1440,
            'availWidth': 2560,
            'availHeight': 1400,
            'colorDepth': 24,
            'pixelDepth': 24,
        },
        'viewport': {
            'width': 1920,
            'height': 1080,
        },
        'webgl': {
            'vendor': 'Google Inc. (Intel)',
            'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)',
        },
    },
    'macos_chrome_131': {
        'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'platform': 'MacIntel',
        'hardwareConcurrency': 8,
        'deviceMemory': 8,
        'maxTouchPoints': 0,
        'vendor': 'Google Inc.',
        'language': 'en-US',
        'languages': ['en-US', 'en'],
        'timezone': 'America/New_York',
        'screen': {
            'width': 2560,
            'height': 1600,
            'availWidth': 2560,
            'availHeight': 1577,
            'colorDepth': 24,
            'pixelDepth': 24,
        },
        'viewport': {
            'width': 1920,
            'height': 1080,
        },
        'webgl': {
            'vendor': 'Apple Inc.',
            'renderer': 'Apple M1',
        },
    },
}


async def handle_consent_and_blockages(page, url: str) -> bool:
    """
    Handle consent screens and blocking elements on a page.

    Args:
        page: Playwright page object
        url: URL of the page being accessed

    Returns:
        bool: True if page is accessible after handling, False if blocked
    """
    print(f"Checking for consent/blockages on {url}")

    # Get page content
    if hasattr(page, 'content'):  # For Playwright-based browsers
        page_content = await page.content()
    else:  # For pydoll Tab objects
        result = await page.execute_script("return document.documentElement.outerHTML")
        # Handle potential dict response from pydoll
        if isinstance(result, dict) and 'result' in result:
            page_content = result['result']
        elif isinstance(result, dict) and 'value' in result:
            page_content = result['value']
        elif isinstance(result, str):
            page_content = result
        else:
            page_content = str(result) if result is not None else ""

    # Safety check: ensure content is a string before processing
    if page_content is None or not isinstance(page_content, str):
        print(f"⚠️  Warning: Got invalid content type {type(page_content)} for {url}")
        page_content = ""

    soup = BeautifulSoup(page_content, 'html.parser')

    # Check for consent screen
    consent_indicators = [
        'consent', 'gdpr', 'privacy', 'cookie', 'accept', 'reject',
        'preferences', 'manage', 'settings', 'policy', 'terms'
    ]

    lower_content = page_content.lower()
    has_consent_screen = any(indicator in lower_content for indicator in consent_indicators)

    # Check for bot detection/captcha elements
    bot_detection_indicators = [
        'captcha', 'verify', 'robot', 'challenge', 'security check',
        'access denied', 'blocked', 'unusual traffic', 'please verify',
        'are you a human', 'protection', 'bot', 'automated',
        'confirm you are human', 'human verification', 'verify you are human'
    ]
    has_bot_detection = any(indicator in lower_content for indicator in bot_detection_indicators)

    if has_bot_detection:
        print(f"BOT DETECTION DETECTED on {url}")
        print("  - Page appears to have bot detection/security measures")
        print("  - This may block automated access")

        # Try to handle common bot detection elements
        try:
            # Look for common captcha/verification elements
            captcha_selectors = [
                'iframe[src*="captcha"]',
                'div[aria-label*="captcha"]',
                'div[role="captcha"]',
                '[class*="captcha"]',
                '[class*="challenge"]',
                '[class*="verify"]',
                '[class*="security"]',
                '[data-hcaptcha]',
                '[data-recaptcha]',
                '[class*="protected"]',
                '[class*="bot"]'
            ]

            for captcha_selector in captcha_selectors:
                try:
                    if hasattr(page, 'query_selector_all'):
                        captcha_elements = await page.query_selector_all(captcha_selector)
                    else:
                        # For pydoll Tab objects, use find method or execute_script
                        # Try to find elements using execute_script
                        element_count = await page.execute_script(f'''
                            return document.querySelectorAll('{captcha_selector}').length;
                        ''')
                        captcha_elements = element_count > 0

                    if captcha_elements:
                        print(f"  - Found potential bot detection element: {captcha_selector}")
                        # In automated context, we can't solve captchas, but we can try to hide them
                        await page.evaluate(f'''
                            document.querySelectorAll('{captcha_selector}').forEach(el => {{
                                el.style.display = 'none';
                                el.remove();
                            }});
                        ''')
                except:
                    continue

            # Look for "Begin" button or similar verification buttons on "confirm you are human" pages
            verification_selectors = [
                'button:has-text("Begin"):not(:has-text("Beginner"))',
                'button:has-text("Start"):not(:has-text("Start"))',
                'button:has-text("Continue"):not(:has-text("Cancel"))',
                'button:has-text("Verify")',
                'button:has-text("Confirm")',
                'button:has-text("I am human")',
                'button:has-text("Yes, I am human")',
                '[class*="begin"] button',
                '[class*="start"] button',
                '[class*="verify"] button',
                '[class*="confirm"] button',
                '[class*="human"] button',
                '[id*="begin"]',
                '[id*="start"]',
                '[id*="verify"]',
                '[id*="confirm"]',
                '[id*="human"]'
            ]

            for verification_selector in verification_selectors:
                try:
                    if hasattr(page, 'query_selector_all'):
                        verification_buttons = await page.query_selector_all(verification_selector)
                        for button in verification_buttons:
                            if button and await button.is_visible():
                                print(f"  - Found verification button: {verification_selector}")
                                await button.click()
                                if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                    await page.wait_for_timeout(3000)  # Wait for potential captcha to load
                                else:  # For pydoll Tab objects
                                    await asyncio.sleep(3.0)  # Equivalent wait
                                break
                    else:
                        # For pydoll Tab objects, use find method or execute_script
                        # Check if element exists using execute_script
                        element_exists = await page.execute_script(f'''
                            return document.querySelectorAll('{verification_selector}').length > 0;
                        ''')
                        if element_exists:
                            print(f"  - Found verification button: {verification_selector}")
                            # Click the element using execute_script
                            await page.execute_script(f'''
                                document.querySelector('{verification_selector}').click();
                            ''')
                            if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                await page.wait_for_timeout(3000)  # Wait for potential captcha to load
                            else:  # For pydoll Tab objects
                                await asyncio.sleep(3.0)  # Equivalent wait
                            break
                except:
                    continue

            # Try to detect and handle common captcha types
            try:
                # Check for reCAPTCHA
                if hasattr(page, 'query_selector_all'):
                    recaptcha_frames = await page.query_selector_all('iframe[src*="recaptcha"]')
                    if recaptcha_frames:
                        print("  - Found reCAPTCHA iframe")
                        # For automated solving, we'd normally use a service here
                        # Since we can't solve it automatically, try to hide it
                        await page.evaluate('''
                            document.querySelectorAll('iframe[src*="recaptcha"]').forEach(frame => {
                                frame.style.display = 'none';
                                frame.remove();
                            });
                            document.querySelectorAll('[class*="recaptcha"]').forEach(el => {
                                el.style.display = 'none';
                                el.remove();
                            });
                        ''')
                else:
                    # For pydoll Tab objects, use execute_script to check for reCAPTCHA
                    recaptcha_count = await page.execute_script('''
                        return document.querySelectorAll('iframe[src*="recaptcha"]').length;
                    ''')
                    if recaptcha_count > 0:
                        print("  - Found reCAPTCHA iframe")
                        # Hide it using execute_script
                        await page.evaluate('''
                            document.querySelectorAll('iframe[src*="recaptcha"]').forEach(frame => {
                                frame.style.display = 'none';
                                frame.remove();
                            });
                            document.querySelectorAll('[class*="recaptcha"]').forEach(el => {
                                el.style.display = 'none';
                                el.remove();
                            });
                        ''')

                # Check for hCaptcha
                if hasattr(page, 'query_selector_all'):
                    hcaptcha_frames = await page.query_selector_all('iframe[src*="hcaptcha"]')
                    if hcaptcha_frames:
                        print("  - Found hCaptcha iframe")
                        # Similarly, try to hide it
                        await page.evaluate('''
                            document.querySelectorAll('iframe[src*="hcaptcha"]').forEach(frame => {
                                frame.style.display = 'none';
                                frame.remove();
                            });
                            document.querySelectorAll('[class*="hcaptcha"]').forEach(el => {
                                el.style.display = 'none';
                                el.remove();
                            });
                        ''')
                else:
                    # For pydoll Tab objects, use execute_script to check for hCaptcha
                    hcaptcha_count = await page.execute_script('''
                        return document.querySelectorAll('iframe[src*="hcaptcha"]').length;
                    ''')
                    if hcaptcha_count > 0:
                        print("  - Found hCaptcha iframe")
                        # Hide it using execute_script
                        await page.evaluate('''
                            document.querySelectorAll('iframe[src*="hcaptcha"]').forEach(frame => {
                                frame.style.display = 'none';
                                frame.remove();
                            });
                            document.querySelectorAll('[class*="hcaptcha"]').forEach(el => {
                                el.style.display = 'none';
                                el.remove();
                            });
                        ''')

                # Check for Cloudflare Turnstile
                if hasattr(page, 'query_selector_all'):
                    turnstile_frames = await page.query_selector_all('iframe[src*="turnstile"]')
                    if turnstile_frames:
                        print("  - Found Cloudflare Turnstile iframe")
                        # Hide it
                        await page.evaluate('''
                            document.querySelectorAll('iframe[src*="turnstile"]').forEach(frame => {
                                frame.style.display = 'none';
                                frame.remove();
                            });
                            document.querySelectorAll('[class*="turnstile"]').forEach(el => {
                                el.style.display = 'none';
                                el.remove();
                            });
                        ''')
                else:
                    # For pydoll Tab objects, use execute_script to check for Turnstile
                    turnstile_count = await page.execute_script('''
                        return document.querySelectorAll('iframe[src*="turnstile"]').length;
                    ''')
                    if turnstile_count > 0:
                        print("  - Found Cloudflare Turnstile iframe")
                        # Hide it using execute_script
                        await page.evaluate('''
                            document.querySelectorAll('iframe[src*="turnstile"]').forEach(frame => {
                                frame.style.display = 'none';
                                frame.remove();
                            });
                            document.querySelectorAll('[class*="turnstile"]').forEach(el => {
                                el.style.display = 'none';
                                el.remove();
                            });
                        ''')

                # Try to find and click any remaining challenge elements
                challenge_selectors = [
                    '[class*="challenge"]',
                    '[class*="widget"]',
                    '[class*="frame"]',
                    '[data-widget-type="recaptcha"]',
                    '[data-sitekey]'
                ]

                for challenge_selector in challenge_selectors:
                    try:
                        if hasattr(page, 'query_selector_all'):
                            challenge_elements = await page.query_selector_all(challenge_selector)
                            for element in challenge_elements:
                                if element:
                                    print(f"  - Found potential challenge element: {challenge_selector}")
                                    # Try to click or hide the element
                                    try:
                                        await element.click()
                                    except:
                                        pass  # If click fails, just continue
                                    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                        await page.wait_for_timeout(2000)
                                    else:  # For pydoll Tab objects
                                        await asyncio.sleep(2.0)
                        else:
                            # For pydoll Tab objects, use execute_script to find and handle challenge elements
                            challenge_count = await page.execute_script(f'''
                                return document.querySelectorAll('{challenge_selector}').length;
                            ''')
                            if challenge_count > 0:
                                print(f"  - Found potential challenge element: {challenge_selector}")
                                # Click the element using execute_script
                                await page.execute_script(f'''
                                    document.querySelectorAll('{challenge_selector}')[0].click();
                                ''')
                                if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                    await page.wait_for_timeout(2000)
                                else:  # For pydoll Tab objects
                                    await asyncio.sleep(2.0)
                    except:
                        continue
            except Exception as e:
                print(f"  - Error handling captcha elements: {e}")
        except Exception as e:
            print(f"  - Error handling bot detection: {e}")

    if has_consent_screen:
        print(f"CONSENT SCREEN DETECTED on {url}")
        print("  - Page appears to contain a consent/privacy notice")
        print("  - This may block access to event listings")

        # Try to find and click accept/decline buttons if they exist
        try:
            # Look for common consent buttons with more comprehensive selectors
            consent_buttons = [
                # Text-based selectors
                'button:has-text("Accept"):not(:has-text("Decline"))',
                'button:has-text("I Agree"):not(:has-text("Disagree"))',
                'button:has-text("Continue"):not(:has-text("Cancel"))',
                'button:has-text("Accept all"):not(:has-text("Reject"))',
                'button:has-text("Agree"):not(:has-text("Disagree"))',
                'button:has-text("Yes"):not(:has-text("No"))',
                'button:has-text("OK")',
                'button:has-text("Close")',
                'button:has-text("Allow")',
                'button:has-text("Allow all")',

                # ID-based selectors
                '[id*="accept"]',
                '[id*="consent"] button',
                '[id*="cookie"] button',
                '[id*="privacy"] button',

                # Class-based selectors
                '[class*="accept"] button',
                '[class*="consent"] button',
                '[class*="cookie"] button',
                '[class*="privacy"] button',
                '[class*="banner"] button',
                '[class*="dialog"] button',
                '[class*="modal"] button',

                # Data attribute selectors
                '[data-testid*="accept"]',
                '[data-testid*="consent"]',
                '[data-testid*="cookie"]',
                '[aria-label*="accept"]',
                '[aria-label*="consent"]',

                # Generic selectors that might catch consent elements
                'button[type="button"]',
                'button[type="submit"]',
                'button',
                '[role="button"]',
            ]

            consent_handled = False
            for btn_selector in consent_buttons:
                try:
                    buttons = await page.query_selector_all(btn_selector)
                    for button in buttons:
                        if button:
                            # Check if button is visible and enabled
                            is_visible = await button.is_visible()
                            is_enabled = await button.is_enabled()

                            if is_visible and is_enabled:
                                # Additional check: see if this button is related to consent
                                button_text = await button.inner_text()
                                button_lower_text = button_text.lower()

                                # Only click if it's likely a consent button
                                consent_related = any(word in button_lower_text for word in [
                                    'accept', 'agree', 'continue', 'allow', 'close', 'ok', 'yes'
                                ])

                                if consent_related:
                                    print(f"  - Found and clicking consent button: '{button_text}' ({btn_selector})")
                                    await button.click()
                                    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                        await page.wait_for_timeout(3000)  # Wait for page to update
                                    else:  # For pydoll Tab objects
                                        await asyncio.sleep(3.0)

                                    # Check if consent screen is gone
                                    if hasattr(page, 'content'):  # For Playwright-based browsers
                                        new_content = await page.content()
                                    else:  # For pydoll Tab objects
                                        result = await page.execute_script("return document.documentElement.outerHTML")
                                        # Handle potential dict response from pydoll
                                        if isinstance(result, dict) and 'result' in result:
                                            new_content = result['result']
                                        elif isinstance(result, dict) and 'value' in result:
                                            new_content = result['value']
                                        elif isinstance(result, str):
                                            new_content = result
                                        else:
                                            new_content = str(result) if result is not None else ""

                                    # Safety check: ensure content is a string before processing
                                    if new_content is None or not isinstance(new_content, str):
                                        print(f"⚠️  Warning: Got invalid content type {type(new_content)} when checking consent dismissal")
                                        new_content = ""

                                    if not any(indicator in new_content.lower() for indicator in consent_indicators):
                                        print("  - Consent screen appears to be dismissed")
                                        consent_handled = True
                                        break

                    if consent_handled:
                        break
                except Exception as e:
                    continue  # Try next selector

            # If still no consent handled, try keyboard-based approach
            if not consent_handled:
                try:
                    # Try pressing Escape key to close modal overlays
                    if hasattr(page, 'keyboard') and hasattr(page.keyboard, 'press'):
                        await page.keyboard.press('Escape')
                    else:
                        # For pydoll Tab objects, use execute_script to simulate key press
                        await page.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));")

                    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                        await page.wait_for_timeout(2000)
                    else:  # For pydoll Tab objects
                        await asyncio.sleep(2.0)

                    # Check if consent screen is gone after Escape
                    if hasattr(page, 'content'):  # For Playwright-based browsers
                        new_content = await page.content()
                    else:  # For pydoll Tab objects
                        result = await page.execute_script("return document.documentElement.outerHTML")
                        # Handle potential dict response from pydoll
                        if isinstance(result, dict) and 'result' in result:
                            new_content = result['result']
                        elif isinstance(result, dict) and 'value' in result:
                            new_content = result['value']
                        elif isinstance(result, str):
                            new_content = result
                        else:
                            new_content = str(result) if result is not None else ""

                    # Safety check: ensure content is a string before processing
                    if new_content is None or not isinstance(new_content, str):
                        print(f"⚠️  Warning: Got invalid content type {type(new_content)} when checking consent dismissal after Escape")
                        new_content = ""

                    if not any(indicator in new_content.lower() for indicator in consent_indicators):
                        print("  - Consent screen dismissed using Escape key")
                        consent_handled = True
                    else:
                        # Try Tab and Enter to navigate to hidden accept buttons
                        if hasattr(page, 'keyboard') and hasattr(page.keyboard, 'press'):
                            await page.keyboard.press('Tab')
                        else:
                            # For pydoll Tab objects, use execute_script to simulate key press
                            await page.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Tab'}));")

                        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                            await page.wait_for_timeout(500)
                        else:  # For pydoll Tab objects
                            await asyncio.sleep(0.5)

                        if hasattr(page, 'keyboard') and hasattr(page.keyboard, 'press'):
                            await page.keyboard.press('Enter')
                        else:
                            # For pydoll Tab objects, use execute_script to simulate key press
                            await page.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));")

                        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                            await page.wait_for_timeout(2000)
                        else:  # For pydoll Tab objects
                            await asyncio.sleep(2.0)

                        # Check again
                        if hasattr(page, 'content'):  # For Playwright-based browsers
                            new_content = await page.content()
                        else:  # For pydoll Tab objects
                            result = await page.execute_script("return document.documentElement.outerHTML")
                            # Handle potential dict response from pydoll
                            if isinstance(result, dict) and 'result' in result:
                                new_content = result['result']
                            elif isinstance(result, dict) and 'value' in result:
                                new_content = result['value']
                            elif isinstance(result, str):
                                new_content = result
                            else:
                                new_content = str(result) if result is not None else ""

                        # Safety check: ensure content is a string before processing
                        if new_content is None or not isinstance(new_content, str):
                            print(f"⚠️  Warning: Got invalid content type {type(new_content)} when checking consent dismissal after keyboard navigation")
                            new_content = ""

                        if not any(indicator in new_content.lower() for indicator in consent_indicators):
                            print("  - Consent screen dismissed using keyboard navigation")
                            consent_handled = True
                except Exception as e:
                    print(f"  - Keyboard approach failed: {e}")

            if not consent_handled:
                print("  - No consent buttons could be automatically clicked")

                # Try an alternative approach: look for overlay elements and try to close them
                try:
                    overlay_selectors = [
                        '[class*="overlay"]',
                        '[class*="backdrop"]',
                        '[class*="modal"]',
                        '[class*="popup"]',
                        '[class*="banner"]',
                        'div[style*="position: fixed"]',
                        'div[style*="z-index:"]',
                    ]

                    for overlay_selector in overlay_selectors:
                        if hasattr(page, 'query_selector_all'):
                            overlays = await page.query_selector_all(overlay_selector)
                            for overlay in overlays:
                                try:
                                    # Try to find a close button within the overlay
                                    if hasattr(overlay, 'query_selector_all'):
                                        close_btns = await overlay.query_selector_all('button, [class*="close"], [class*="dismiss"], [aria-label*="close"]')
                                        for close_btn in close_btns:
                                            if close_btn and await close_btn.is_visible():
                                                print(f"  - Attempting to close overlay with close button")
                                                await close_btn.click()
                                                if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                                    await page.wait_for_timeout(2000)
                                                else:  # For pydoll Tab objects
                                                    await asyncio.sleep(2.0)
                                                break
                                    else:
                                        # For pydoll Tab objects, use execute_script to find and close overlays
                                        await page.execute_script(f'''
                                            document.querySelectorAll('{overlay_selector}').forEach(overlay => {{
                                                const closeButtons = overlay.querySelectorAll('button, [class*="close"], [class*="dismiss"], [aria-label*="close"]');
                                                if (closeButtons.length > 0) {{
                                                    closeButtons[0].click();
                                                    console.log("Closed overlay with close button");
                                                }}
                                            }});
                                        ''');
                                        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                            await page.wait_for_timeout(2000)
                                        else:  # For pydoll Tab objects
                                            await asyncio.sleep(2.0)
                                        break
                                except:
                                    continue
                        else:
                            # For pydoll Tab objects, use execute_script to find and close overlays
                            await page.execute_script(f'''
                                document.querySelectorAll('{overlay_selector}').forEach(overlay => {{
                                    const closeButtons = overlay.querySelectorAll('button, [class*="close"], [class*="dismiss"], [aria-label*="close"]');
                                    if (closeButtons.length > 0) {{
                                        closeButtons[0].click();
                                        console.log("Closed overlay with close button");
                                    }}
                                }});
                            ''');
                            if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                                await page.wait_for_timeout(2000)
                            else:  # For pydoll Tab objects
                                await asyncio.sleep(2.0)
                            break
                except:
                    pass

                # If still not handled, try to evaluate JavaScript to remove consent elements
                try:
                    # Remove cookie consent banners using JavaScript
                    await page.evaluate("""
                        // Remove common consent/cookie banner elements
                        const consentElements = document.querySelectorAll('[class*="consent"], [class*="cookie"], [class*="privacy"], [class*="banner"], [class*="modal"]');
                        consentElements.forEach(element => {
                            if (element) {
                                element.style.display = 'none';
                                element.remove();
                            }
                        });

                        // Remove elements with common consent IDs
                        const consentIds = ['consent', 'cookie', 'privacy', 'banner', 'modal'];
                        consentIds.forEach(id => {
                            const element = document.getElementById(id);
                            if (element) {
                                element.style.display = 'none';
                                element.remove();
                            }
                        });

                        // Remove elements with data-testid containing consent-related terms
                        const consentDataElements = document.querySelectorAll('[data-testid*="consent"], [data-testid*="cookie"], [data-testid*="privacy"]');
                        consentDataElements.forEach(element => {
                            if (element) {
                                element.style.display = 'none';
                                element.remove();
                            }
                        });
                    """)
                    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                        await page.wait_for_timeout(2000)
                    else:  # For pydoll Tab objects
                        await asyncio.sleep(2.0)

                    # Check if consent screen is gone after JavaScript removal
                    if hasattr(page, 'content'):  # For Playwright-based browsers
                        new_content = await page.content()
                    else:  # For pydoll Tab objects
                        result = await page.execute_script("return document.documentElement.outerHTML")
                        # Handle potential dict response from pydoll
                        if isinstance(result, dict) and 'result' in result:
                            new_content = result['result']
                        elif isinstance(result, dict) and 'value' in result:
                            new_content = result['value']
                        elif isinstance(result, str):
                            new_content = result
                        else:
                            new_content = str(result) if result is not None else ""

                    # Safety check: ensure content is a string before processing
                    if new_content is None or not isinstance(new_content, str):
                        print(f"⚠️  Warning: Got invalid content type {type(new_content)} when checking consent dismissal after JavaScript removal")
                        new_content = ""

                    if not any(indicator in new_content.lower() for indicator in consent_indicators):
                        print("  - Consent screen removed using JavaScript")
                        consent_handled = True
                except Exception as js_error:
                    print(f"  - JavaScript removal failed: {js_error}")

        except Exception as e:
            print(f"  - Error handling consent screen: {e}")

    # Check for other potential blocking elements
    blocking_indicators = ['blocked', 'access denied', 'captcha', 'verify', 'robot', 'challenge']
    has_blocking_element = any(indicator in lower_content for indicator in blocking_indicators)

    if has_blocking_element:
        print(f"BLOCKING ELEMENT DETECTED on {url}")
        print("  - Page may be blocked or require manual intervention")

    # Check for common error indicators in the content
    error_indicators = [
        '404', 'not found', 'error', 'unavailable', 'temporarily',
        'maintenance', 'offline', 'blocked', 'access denied', 'forbidden',
        'rate limit', 'too many requests', 'request blocked'
    ]
    page_text = soup.get_text().lower()
    has_error = any(indicator in page_text for indicator in error_indicators)

    if has_error:
        print(f"PAGE CONTENT ERROR on {url}")
        print("  - Content suggests the page did not load properly")

    # Check if the page has the expected content structure for Eventbrite
    # Look for common Eventbrite elements that should be present on event listing pages
    expected_elements = [
        soup.find_all('a', href=lambda x: x and ('/e/' in x or '/events/' in x)),
        soup.find_all(class_=lambda x: x and 'event' in str(x).lower()),
        soup.find_all('h3'),  # Event titles are often in h3 tags
    ]

    has_expected_content = any(len(elements) > 0 for elements in expected_elements)

    if not has_expected_content and not has_error:
        print(f"MISSING EXPECTED CONTENT on {url}")
        print("  - Page may not have loaded the event listings properly")

    # Return True if page seems accessible (doesn't have blocking elements)
    return not (has_blocking_element and has_error)


async def solve_captcha_if_present(page):
    """
    Attempt to solve any captcha that might be present on the page.
    This function tries multiple approaches to handle captchas.
    """
    try:
        # Check for different types of captchas
        captcha_detected = False

        # Check for reCAPTCHA
        if hasattr(page, 'query_selector_all'):
            recaptcha_frames = await page.query_selector_all('iframe[src*="recaptcha"]')
            if recaptcha_frames:
                print("reCAPTCHA detected")
                captcha_detected = True
                # Try to solve using a service (would require API key in real implementation)
                # For now, we'll try to bypass by hiding or simulating completion
                await page.evaluate("""
                    // Try to simulate reCAPTCHA completion
                    if (typeof grecaptcha !== 'undefined') {
                        for (let widgetId in grecaptcha.renderedWidgets) {
                            try {
                                grecaptcha.reset(widgetId);
                            } catch(e) {}
                        }
                    }

                    // Hide all recaptcha elements
                    document.querySelectorAll('iframe[src*="recaptcha"], div[class*="recaptcha"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    });
                """)
        else:
            # For pydoll Tab objects, use execute_script to check for reCAPTCHA
            recaptcha_count = await page.execute_script('''
                return document.querySelectorAll('iframe[src*="recaptcha"]').length;
            ''')
            if recaptcha_count > 0:
                print("reCAPTCHA detected")
                captcha_detected = True
                # Hide all recaptcha elements using execute_script
                await page.evaluate("""
                    // Hide all recaptcha elements
                    document.querySelectorAll('iframe[src*="recaptcha"], div[class*="recaptcha"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    });
                """)

        # Check for hCaptcha
        if hasattr(page, 'query_selector_all'):
            hcaptcha_frames = await page.query_selector_all('iframe[src*="hcaptcha"]')
            if hcaptcha_frames:
                print("hCaptcha detected")
                captcha_detected = True
                await page.evaluate("""
                    // Hide all hcaptcha elements
                    document.querySelectorAll('iframe[src*="hcaptcha"], div[class*="hcaptcha"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    });
                """)
        else:
            # For pydoll Tab objects, use execute_script to check for hCaptcha
            hcaptcha_count = await page.execute_script('''
                return document.querySelectorAll('iframe[src*="hcaptcha"]').length;
            ''')
            if hcaptcha_count > 0:
                print("hCaptcha detected")
                captcha_detected = True
                await page.evaluate("""
                    // Hide all hcaptcha elements
                    document.querySelectorAll('iframe[src*="hcaptcha"], div[class*="hcaptcha"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    });
                """)

        # Check for Cloudflare Turnstile
        if hasattr(page, 'query_selector_all'):
            turnstile_frames = await page.query_selector_all('iframe[src*="turnstile"]')
            if turnstile_frames:
                print("Cloudflare Turnstile detected")
                captcha_detected = True
                await page.evaluate("""
                    // Hide all turnstile elements
                    document.querySelectorAll('iframe[src*="turnstile"], div[class*="turnstile"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    });
                """)
        else:
            # For pydoll Tab objects, use execute_script to check for Turnstile
            turnstile_count = await page.execute_script('''
                return document.querySelectorAll('iframe[src*="turnstile"]').length;
            ''')
            if turnstile_count > 0:
                print("Cloudflare Turnstile detected")
                captcha_detected = True
                await page.evaluate("""
                    // Hide all turnstile elements
                    document.querySelectorAll('iframe[src*="turnstile"], div[class*="turnstile"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    });
                """)

        # If any captcha was detected, wait a bit for the page to adjust
        if captcha_detected:
            if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                await page.wait_for_timeout(3000)
            else:  # For pydoll Tab objects
                await asyncio.sleep(3.0)
            return True
        else:
            return False

    except Exception as e:
        print(f"Error in solve_captcha_if_present: {e}")
        return False


async def wait_for_page_load(page, timeout: int = 10000):
    """
    Wait for page to load completely with multiple strategies.

    Args:
        page: Playwright page object
        timeout: Maximum time to wait in milliseconds
    """
    try:
        # Wait for network to be idle
        await page.wait_for_load_state("networkidle", timeout=min(timeout, 30000))
    except:
        # If network idle takes too long, just wait a bit
        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
            await page.wait_for_timeout(min(timeout, 5000))
        else:  # For pydoll Tab objects
            await asyncio.sleep(min(timeout, 5000)/1000.0)  # Convert ms to seconds

    # Additional wait for dynamic content
    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
        await page.wait_for_timeout(3000)
    else:  # For pydoll Tab objects
        await asyncio.sleep(3.0)

    # Sometimes we need to wait a bit more after consent handling
    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
        await page.wait_for_timeout(2000)
    else:  # For pydoll Tab objects
        await asyncio.sleep(2.0)


async def check_page_status(page, url: str) -> tuple[bool, str]:
    """
    Check if page loaded successfully and is accessible.

    Args:
        page: Playwright page object
        url: URL of the page

    Returns:
        tuple: (is_accessible, status_message)
    """
    try:
        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Check title
        title = soup.title.string if soup.title else ""
        if title and ("error" in title.lower() or "not found" in title.lower()):
            return False, f"Page title indicates error: '{title}'"

        # Check for common error messages
        page_text = soup.get_text().lower()
        error_indicators = [
            '404', 'not found', 'error', 'unavailable', 'temporarily',
            'maintenance', 'offline', 'blocked', 'access denied', 'forbidden',
            'rate limit', 'too many requests', 'request blocked', 'unusual traffic',
            'verify you are human', 'captcha', 'robot', 'challenge', 'security check'
        ]

        for indicator in error_indicators:
            if indicator in page_text:
                return False, f"Error indicator '{indicator}' found in page content"

        # Check if page has event-related content
        event_links = soup.find_all('a', href=lambda x: x and ('/e/' in x and 'eventbrite' in x.lower()))
        if len(event_links) == 0:
            # Check for other possible event indicators
            event_elements = soup.find_all(class_=lambda x: x and 'event' in str(x).lower() if x else False)
            if len(event_elements) == 0:
                # Check for search results or event listings
                search_results = soup.find_all(class_=lambda x: x and 'search' in str(x).lower() if x else False)
                event_listings = soup.find_all(class_=lambda x: x and 'listing' in str(x).lower() if x else False)

                if len(search_results) == 0 and len(event_listings) == 0:
                    # Check for specific Eventbrite elements that should be present
                    eventbrite_specific = soup.find_all(class_=lambda x: x and (
                        'search-result' in str(x).lower() or
                        'event-card' in str(x).lower() or
                        'event-list' in str(x).lower() or
                        'discover' in str(x).lower()
                    ) if x else False)

                    if len(eventbrite_specific) == 0:
                        # Check for any h3 tags which usually contain event titles
                        h3_tags = soup.find_all('h3')
                        if len(h3_tags) == 0:
                            return False, "No event-related content found on page - no event cards, listings, or titles detected"

        return True, "Page loaded successfully"

    except Exception as e:
        return False, f"Exception while checking page status: {str(e)}"


ANTI_AUTOMATION_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

ANTI_AUTOMATION_DESKTOP_VIEWPORTS = [
    {"width": 1280, "height": 720},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]

ANTI_AUTOMATION_MOBILE_VIEWPORTS = [
    {"width": 390, "height": 844},
    {"width": 414, "height": 896},
    {"width": 428, "height": 926},
]

ANTI_AUTOMATION_ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.8,fr;q=0.6",
]

CAPTCHA_SOLVER_BASE_URL = "https://2captcha.com"
CAPTCHA_METHODS = {
    "recaptcha": "userrecaptcha",
    "hcaptcha": "hcaptcha",
    "turnstile": "turnstile",
}
CAPTCHA_POLL_INTERVAL = 5
CAPTCHA_POLL_TIMEOUT = 120

# Free CAPTCHA solving services
NOPECHA_API_URL = "https://api.nopecha.com"
ANTICAPTCHA_API_URL = "https://api.anti-captcha.com"


async def create_undetected_browser(use_pydoll=True, use_patchright=True, use_botright=False, headless=True, profile_name=None):
    """
    Create an undetected browser instance using the best available method.
    Priority: Patchright > Playwright > Botright > pydoll (fallback)
    
    Args:
        use_pydoll: Enable pydoll (Cloudflare bypass) - used as fallback
        use_patchright: Enable Patchright (enhanced stealth)
        use_botright: Enable Botright (advanced anti-detection)
        headless: Run in headless mode
        profile_name: Specific browser profile to use (e.g., 'windows_chrome_131')
    
    Returns: (browser, page, browser_type) tuple
    browser_type: 'pydoll', 'patchright', 'botright', or 'playwright'
    """
    
    # Select a real browser profile
    if profile_name and profile_name in REAL_BROWSER_PROFILES:
        profile = REAL_BROWSER_PROFILES[profile_name]
    else:
        # Randomly select a profile for variety
        profile = random.choice(list(REAL_BROWSER_PROFILES.values()))
    
    print(f"📋 Using profile: {profile['userAgent'][:50]}...")
    
    # Method 1: Patchright (enhanced Playwright with stealth) - PRIMARY
    if use_patchright and PATCHRIGHT_AVAILABLE:
        try:
            print("🚀 Using Patchright browser (enhanced stealth)...")
            from patchright.async_api import async_playwright

            # Use start() instead of async with to keep browser alive
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-infobars',
                    f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}',
                    '--start-maximized',
                    '--disable-gpu',
                    '--disable-extensions',
                ]
            )

            context = await browser.new_context(
                viewport=profile['viewport'],
                user_agent=profile['userAgent'],
                locale=profile['language'],
                timezone_id=profile['timezone'],
                color_scheme='light',
                device_scale_factor=1,
                has_touch=profile['maxTouchPoints'] > 0,
                screen={
                    'width': profile['screen']['width'],
                    'height': profile['screen']['height'],
                },
            )

            page = await context.new_page()

            # Apply consistent fingerprint
            await apply_consistent_fingerprint_playwright(page, profile)

            # Store playwright instance on browser to prevent garbage collection
            browser._playwright = playwright

            print("✅ Patchright browser created successfully")
            return browser, page, 'patchright'

        except Exception as e:
            print(f"⚠️  Patchright failed: {e}, falling back...")
    
    # Method 2: Standard Playwright with enhanced anti-detection
    print("🚀 Using standard Playwright with enhanced anti-detection...")
    try:
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-infobars',
                f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}',
                '--start-maximized',
                '--disable-gpu',
                '--disable-extensions',
            ]
        )
        
        context = await browser.new_context(
            viewport=profile['viewport'],
            user_agent=profile['userAgent'],
            locale=profile['language'],
            timezone_id=profile['timezone'],
            screen={
                'width': profile['screen']['width'],
                'height': profile['screen']['height'],
            },
        )
        
        page = await context.new_page()
        
        # Apply stealth scripts
        await apply_consistent_fingerprint_playwright(page, profile)
        
        # Store playwright instance on browser to prevent garbage collection
        browser._playwright = playwright
        
        print("✅ Playwright browser created successfully")
        return browser, page, 'playwright'
        
    except Exception as e:
        print(f"⚠️  Playwright failed: {e}, falling back...")
    
    # Method 3: Botright (advanced anti-detection)
    if use_botright and BOTRIGHT_AVAILABLE:
        try:
            print("🚀 Using Botright browser (advanced anti-detection)...")
            botright_client = await botright.Botright()
            browser = await botright_client.new_browser()
            page = await browser.new_page()
            
            print("✅ Botright browser created successfully")
            return browser, page, 'botright'
            
        except Exception as e:
            print(f"⚠️  Botright failed: {e}, falling back...")
    
    # Method 4: pydoll (fallback for Cloudflare) - LAST RESORT
    if use_pydoll and PYDOLL_AVAILABLE:
        try:
            print("🚀 Using pydoll browser (Cloudflare bypass fallback)...")

            # Configure pydoll with real browser profile
            options = ChromiumOptions()

            # Set browser preferences for realism
            options.browser_preferences = {
                # Simulate usage history (90 days old profile)
                'profile': {
                    'created_by_version': '120.0.6099.130',
                    'creation_time': str(time.time() - (90 * 24 * 60 * 60)),
                    'exit_type': 'Normal',
                },
                # Realistic content settings
                'profile.default_content_setting_values': {
                    'cookies': 1,
                    'images': 1,
                    'javascript': 1,
                    'notifications': 2,  # Ask (realistic)
                    'plugins': 1,
                    'popups': 0,
                    'geolocation': 2,
                    'media_stream': 2,
                },
                # WebRTC IP handling (prevent leaks)
                'webrtc': {
                    'ip_handling_policy': 'disable_non_proxied_udp',
                },
            }

            # Add arguments for stealth
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument(f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')  # Helps with stability
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Faster loading

            if headless:
                options.add_argument('--headless=new')

            browser = PydollChrome(options=options)

            # Add timeout for browser start
            try:
                await asyncio.wait_for(browser.start(), timeout=30.0)
            except asyncio.TimeoutError:
                raise Exception("pydoll browser start timeout")

            # Get the page from pydoll - the API has changed
            # Pydoll's start() method returns a Tab object that acts as the page
            page = await browser.start()  # This returns the Tab object

            # Apply consistent fingerprint using CDP
            await apply_consistent_fingerprint_pydoll(page, profile)

            # Enable automatic Cloudflare captcha solving
            await page.enable_auto_solve_cloudflare_captcha()

            print("✅ pydoll browser created successfully")
            return browser, page, 'pydoll'

        except Exception as e:
            print(f"⚠️  pydoll failed: {e}")
    
    # If all methods failed
    raise Exception("All browser creation methods failed")


async def apply_consistent_fingerprint_pydoll(page, profile: Dict):
    """Apply consistent browser fingerprint to pydoll page using JavaScript injection"""
    try:
        # Inject consistent fingerprint script using JavaScript instead of CDP commands
        await page.execute_script(f'''
            () => {{
                // Override navigator properties
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => {profile['hardwareConcurrency']}
                }});

                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {profile['deviceMemory']}
                }});

                Object.defineProperty(navigator, 'maxTouchPoints', {{
                    get: () => {profile['maxTouchPoints']}
                }});

                Object.defineProperty(navigator, 'vendor', {{
                    get: () => '{profile['vendor']}'
                }});

                Object.defineProperty(navigator, 'languages', {{
                    get: () => {json.dumps(profile['languages'])}
                }});

                // Override screen properties
                Object.defineProperty(screen, 'width', {{
                    get: () => {profile['screen']['width']}
                }});

                Object.defineProperty(screen, 'height', {{
                    get: () => {profile['screen']['height']}
                }});

                Object.defineProperty(screen, 'availWidth', {{
                    get: () => {profile['screen']['availWidth']}
                }});

                Object.defineProperty(screen, 'availHeight', {{
                    get: () => {profile['screen']['availHeight']}
                }});

                Object.defineProperty(screen, 'colorDepth', {{
                    get: () => {profile['screen']['colorDepth']}
                }});

                Object.defineProperty(screen, 'pixelDepth', {{
                    get: () => {profile['screen']['pixelDepth']}
                }});

                // Override WebGL
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{profile['webgl']['vendor']}';
                    }}
                    if (parameter === 37446) {{
                        return '{profile['webgl']['renderer']}';
                    }}
                    return getParameter.call(this, parameter);
                }};

                // Override user agent via navigator
                Object.defineProperty(navigator, 'userAgent', {{
                    get: () => '{profile['userAgent']}'
                }});

                // Override platform
                Object.defineProperty(navigator, 'platform', {{
                    get: () => '{profile['platform']}'
                }});

                // Hide webdriver property
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined
                }});

                console.log('✅ Consistent fingerprint applied');
            }}
        ''')

        print("✅ Applied consistent fingerprint to pydoll browser")

    except Exception as e:
        print(f"⚠️  Error applying fingerprint: {e}")


async def apply_consistent_fingerprint_playwright(page, profile: Dict):
    """Apply consistent browser fingerprint to Playwright/Patchright page"""
    try:
        # Add init script for consistent fingerprint
        await page.add_init_script(f'''
            () => {{
                // Override navigator properties
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => {profile['hardwareConcurrency']}
                }});
                
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {profile['deviceMemory']}
                }});
                
                Object.defineProperty(navigator, 'maxTouchPoints', {{
                    get: () => {profile['maxTouchPoints']}
                }});
                
                Object.defineProperty(navigator, 'vendor', {{
                    get: () => '{profile['vendor']}'
                }});
                
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined
                }});
                
                // Override WebGL
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{profile['webgl']['vendor']}';
                    }}
                    if (parameter === 37446) {{
                        return '{profile['webgl']['renderer']}';
                    }}
                    return getParameter.call(this, parameter);
                }};
                
                // Add chrome object
                window.chrome = {{
                    runtime: {{}},
                    loadTimes: function() {{}},
                    csi: function() {{}},
                    app: {{}}
                }};
                
                console.log('✅ Consistent fingerprint applied');
            }}
        ''')
        
        print("✅ Applied consistent fingerprint to Playwright browser")
        
    except Exception as e:
        print(f"⚠️  Error applying fingerprint: {e}")


async def close_undetected_browser(browser, browser_type):
    """Close browser based on its type"""
    try:
        if browser_type == 'pydoll':
            await browser.stop()
        elif browser_type in ['patchright', 'botright', 'playwright']:
            await browser.close()
    except Exception as e:
        print(f"Error closing browser: {e}")


async def verify_fingerprint_consistency(page, browser_type='playwright') -> Tuple[bool, List[str]]:
    """
    Verify that the browser fingerprint is consistent and realistic.
    Returns: (is_consistent, list_of_issues)
    """
    issues = []
    
    try:
        if browser_type == 'pydoll':
            # Use pydoll's execute_script
            fingerprint = await page.execute_script('''
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        hardwareConcurrency: navigator.hardwareConcurrency,
                        deviceMemory: navigator.deviceMemory,
                        webdriver: navigator.webdriver,
                        languages: navigator.languages,
                        vendor: navigator.vendor,
                        maxTouchPoints: navigator.maxTouchPoints,
                        screen: {
                            width: screen.width,
                            height: screen.height,
                            colorDepth: screen.colorDepth,
                        },
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    };
                }
            ''')
        else:
            # Use Playwright's evaluate
            fingerprint = await page.evaluate('''
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        hardwareConcurrency: navigator.hardwareConcurrency,
                        deviceMemory: navigator.deviceMemory,
                        webdriver: navigator.webdriver,
                        languages: navigator.languages,
                        vendor: navigator.vendor,
                        maxTouchPoints: navigator.maxTouchPoints,
                        screen: {
                            width: screen.width,
                            height: screen.height,
                            colorDepth: screen.colorDepth,
                        },
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    };
                }
            ''')
        
        # Check for webdriver
        if fingerprint.get('webdriver') == True:
            issues.append("navigator.webdriver is true (DETECTED)")
        
        # Check platform consistency
        ua = fingerprint.get('userAgent', '')
        platform = fingerprint.get('platform', '')
        
        if 'Windows' in ua and 'Win' not in platform:
            issues.append(f"Platform mismatch: UA says Windows, platform says {platform}")
        elif 'Mac' in ua and 'Mac' not in platform:
            issues.append(f"Platform mismatch: UA says Mac, platform says {platform}")
        elif 'Linux' in ua and 'Linux' not in platform:
            issues.append(f"Platform mismatch: UA says Linux, platform says {platform}")
        
        # Check hardware consistency
        cores = fingerprint.get('hardwareConcurrency', 0)
        if cores < 2 or cores > 32:
            issues.append(f"Unrealistic CPU cores: {cores}")
        
        memory = fingerprint.get('deviceMemory', 0)
        if memory and (memory < 2 or memory > 32):
            issues.append(f"Unrealistic device memory: {memory}GB")
        
        # Check vendor
        vendor = fingerprint.get('vendor', '')
        if not vendor or vendor == '':
            issues.append("Missing vendor property")
        
        # Check languages
        languages = fingerprint.get('languages', [])
        if not languages or len(languages) == 0:
            issues.append("No languages defined")
        
        # Check screen resolution
        screen_width = fingerprint.get('screen', {}).get('width', 0)
        if screen_width < 800 or screen_width > 7680:
            issues.append(f"Unrealistic screen width: {screen_width}")
        
        is_consistent = len(issues) == 0
        
        if is_consistent:
            print("✅ Fingerprint consistency check PASSED")
        else:
            print(f"⚠️  Fingerprint consistency check FAILED ({len(issues)} issues)")
            for issue in issues:
                print(f"    - {issue}")
        
        return is_consistent, issues
        
    except Exception as e:
        print(f"⚠️  Error verifying fingerprint: {e}")
        return False, [f"Verification error: {str(e)}"]


@pydoll_retry(max_retries=2, delay=3.0, backoff=1.5)
async def navigate_with_cloudflare_bypass(page, url, browser_type='playwright', timeout=30000):
    """
    Navigate to URL with automatic Cloudflare bypass if using pydoll.
    Includes human-like delays and behavior with retry logic.
    """
    if browser_type == 'pydoll' and PYDOLL_AVAILABLE:
        try:
            print(f"🌐 Navigating with Cloudflare bypass: {url}")
            
            # Add random delay before navigation (human-like)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Use context manager for automatic captcha handling
            async with page.expect_and_bypass_cloudflare_captcha(
                time_before_click=random.randint(2, 6),
                custom_selector=(By.ID, 'challenge-form') if random.choice([True, False]) else None
            ):
                await page.go_to(url)
                print("✅ Cloudflare bypass completed")
            
            # Random delay after page load (human-like)
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Simulate human behavior: random scroll
            try:
                scroll_amount = random.randint(100, 500)
                await page.execute_script(f'window.scrollTo(0, {scroll_amount});')
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await page.execute_script('window.scrollTo(0, 0);')
            except:
                pass
            
            return True
        except Exception as e:
            print(f"⚠️  Cloudflare bypass error: {e}")
            # Fallback to regular navigation
            try:
                await page.go_to(url)
                return True
            except Exception as fallback_error:
                print(f"⚠️  Fallback navigation also failed: {fallback_error}")
                raise fallback_error
    else:
        # Standard navigation for other browser types with human-like behavior
        try:
            # Random delay before navigation
            await asyncio.sleep(random.uniform(0.3, 1.0))
            
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Random delay after navigation
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Simulate human scroll behavior
            try:
                await page.evaluate(f"window.scrollTo(0, {random.randint(100, 300)});")
                await asyncio.sleep(random.uniform(0.2, 0.6))
            except:
                pass
            
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            raise e


# Free CAPTCHA solving services
NOPECHA_API_URL = "https://api.nopecha.com"
ANTICAPTCHA_API_URL = "https://api.anti-captcha.com"


def _build_anti_detection_script(user_agent: str, languages: str, viewport: Dict[str, int]) -> str:
    """Enhanced anti-detection script with more comprehensive evasion techniques"""
    language_list = [lang.strip() for lang in languages.split(",") if lang.strip()]
    languages_literal = json.dumps(language_list or ["en-US", "en"])

    return f"""
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        
        // Override user agent
        Object.defineProperty(navigator, 'userAgent', {{ get: () => '{user_agent}' }});
        
        // Override languages
        Object.defineProperty(navigator, 'language', {{ get: () => '{language_list[0] if language_list else 'en-US'}' }});
        Object.defineProperty(navigator, 'languages', {{ get: () => {languages_literal} }});
        
        // Override platform
        Object.defineProperty(navigator, 'platform', {{ get: () => 'Win32' }});
        
        // Override hardware properties
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => 8 }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {random.randint(4, 16)} }});
        
        // Add chrome object
        window.chrome = {{ 
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {{ 
            get: () => [
                {{
                    0: {{type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"}},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }},
                {{
                    0: {{type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"}},
                    description: "Portable Document Format",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                }},
                {{
                    0: {{type: "application/x-nacl", suffixes: "", description: "Native Client Executable"}},
                    1: {{type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"}},
                    description: "",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }}
            ]
        }});
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );
        
        // Override window dimensions
        Object.defineProperty(window, 'outerWidth', {{ get: () => {viewport['width']} }});
        Object.defineProperty(window, 'outerHeight', {{ get: () => {viewport['height']} }});
        Object.defineProperty(window, 'innerWidth', {{ get: () => {viewport['width']} }});
        Object.defineProperty(window, 'innerHeight', {{ get: () => {viewport['height'] - 100} }});
        
        // Override screen properties
        Object.defineProperty(window.screen, 'width', {{ get: () => {viewport['width']} }});
        Object.defineProperty(window.screen, 'height', {{ get: () => {viewport['height']} }});
        Object.defineProperty(window.screen, 'availWidth', {{ get: () => {viewport['width']} }});
        Object.defineProperty(window.screen, 'availHeight', {{ get: () => {viewport['height'] - 40} }});
        
        // Override connection
        Object.defineProperty(navigator, 'connection', {{
            get: () => ({{
                effectiveType: '4g',
                rtt: {random.randint(50, 150)},
                downlink: {random.uniform(1.5, 10.0):.1f},
                saveData: false
            }})
        }});
        
        // Override battery
        navigator.getBattery = () => Promise.resolve({{
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: {random.uniform(0.5, 1.0):.2f}
        }});
        
        // Mask automation frameworks
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        
        // Override toString to hide proxy
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {{
            if (this === navigator.permissions.query) {{
                return 'function query() {{ [native code] }}';
            }}
            return originalToString.call(this);
        }};
        
        // Add realistic timing
        const originalDateNow = Date.now;
        let timeOffset = {random.randint(-50, 50)};
        Date.now = function() {{
            return originalDateNow() + timeOffset;
        }};
        
        // Override canvas fingerprinting
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            const context = this.getContext('2d');
            if (context) {{
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] = imageData.data[i] ^ {random.randint(0, 3)};
                }}
                context.putImageData(imageData, 0, 0);
            }}
            return originalToDataURL.apply(this, arguments);
        }};
        
        // Override WebGL fingerprinting
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return 'Intel Inc.';
            }}
            if (parameter === 37446) {{
                return 'Intel Iris OpenGL Engine';
            }}
            return getParameter.call(this, parameter);
        }};
        
        console.log('Anti-detection measures applied');
    """


async def jitter_mouse_movements(page, steps: int = 4, viewport: Optional[Dict[str, int]] = None):
    if viewport is None:
        viewport = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")

    width = max(1, viewport.get("width", 1280))
    height = max(1, viewport.get("height", 720))

    for _ in range(steps):
        x = random.randint(5, width - 5)
        y = random.randint(5, height - 5)
        await page.mouse.move(x, y, steps=random.randint(5, 12))
        await page.wait_for_timeout(random.randint(80, 200))


async def apply_anti_automation_measures(page, prefer_mobile: bool = False):
    """Enhanced anti-automation measures with comprehensive evasion"""
    user_agent = random.choice(ANTI_AUTOMATION_USER_AGENTS)
    languages = random.choice(ANTI_AUTOMATION_ACCEPT_LANGUAGES)
    viewport = (random.choice(ANTI_AUTOMATION_MOBILE_VIEWPORTS) if prefer_mobile else random.choice(ANTI_AUTOMATION_DESKTOP_VIEWPORTS))

    await page.set_viewport_size(viewport)
    
    # Apply comprehensive anti-detection script
    await page.add_init_script(_build_anti_detection_script(user_agent, languages, viewport))

    # Set realistic headers
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": languages,
        "accept-encoding": "gzip, deflate, br",
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": user_agent,
    }
    await page.set_extra_http_headers(headers)

    # Add random delay to simulate human behavior
    await page.wait_for_timeout(random.randint(800, 2000))
    
    # Perform realistic mouse movements
    await jitter_mouse_movements(page, steps=random.randint(3, 6), viewport=viewport)
    
    # Random scroll
    try:
        await page.evaluate(f"window.scrollTo(0, {random.randint(100, 300)});")
        await page.wait_for_timeout(random.randint(300, 800))
    except:
        pass


async def detect_and_solve_captcha(page, max_wait: int = CAPTCHA_POLL_TIMEOUT) -> bool:
    """
    Enhanced CAPTCHA detection and solving with multiple free services
    Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile
    """
    print("🔍 Checking for CAPTCHAs...")
    
    # Check for API keys
    solver_key = os.environ.get("CAPTCHA_SOLVER_API_KEY") or os.environ.get("CAPTCHA_API_KEY")
    nopecha_key = os.environ.get("NOPECHA_API_KEY")
    anticaptcha_key = os.environ.get("ANTICAPTCHA_API_KEY")
    
    start = time.monotonic()
    while time.monotonic() - start < max_wait:
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Detect CAPTCHA type and sitekey
        captcha_info = await _detect_captcha_on_page(page, soup)
        
        if not captcha_info:
            # No CAPTCHA detected
            return False
        
        captcha_type = captcha_info['type']
        sitekey = captcha_info['sitekey']
        print(f"🤖 Detected {captcha_type} CAPTCHA with sitekey: {sitekey[:20]}...")
        
        # Try multiple solving methods in order of preference
        solution = None
        
        # Method 1: Try NopeCHA (free tier available)
        if nopecha_key and not solution:
            print("  Attempting NopeCHA solver...")
            solution = await solve_captcha_nopecha(nopecha_key, sitekey, page.url, captcha_type)
        
        # Method 2: Try 2Captcha (paid but reliable)
        if solver_key and not solution:
            print("  Attempting 2Captcha solver...")
            solution = await asyncio.to_thread(
                request_captcha_solution, solver_key, sitekey, page.url, captcha_type, max_wait
            )
        
        # Method 3: Try Anti-Captcha
        if anticaptcha_key and not solution:
            print("  Attempting Anti-Captcha solver...")
            solution = await solve_captcha_anticaptcha(anticaptcha_key, sitekey, page.url, captcha_type)
        
        # Method 4: Try automated bypass techniques
        if not solution:
            print("  Attempting automated bypass...")
            bypass_success = await attempt_captcha_bypass(page, captcha_type)
            if bypass_success:
                print("  ✅ CAPTCHA bypassed successfully!")
                return True
        
        # Inject solution if we got one
        if solution:
            print(f"  ✅ Got CAPTCHA solution, injecting...")
            await _inject_captcha_solution(page, solution, captcha_type)
            
            # Wait for page to process the solution
            await page.wait_for_timeout(3000)
            
            # Check if CAPTCHA is still present
            if hasattr(page, 'content'):  # For Playwright-based browsers
                new_content = await page.content()
            else:  # For pydoll Tab objects
                result = await page.execute_script("return document.documentElement.outerHTML")
                # Handle potential dict response from pydoll
                if isinstance(result, dict) and 'result' in result:
                    new_content = result['result']
                elif isinstance(result, dict) and 'value' in result:
                    new_content = result['value']
                elif isinstance(result, str):
                    new_content = result
                else:
                    new_content = str(result) if result is not None else ""

            # Safety check: ensure content is a string before processing
            if new_content is None or not isinstance(new_content, str):
                print(f"⚠️  Warning: Got invalid content type {type(new_content)} when checking CAPTCHA status")
                new_content = ""

            new_soup = BeautifulSoup(new_content, 'html.parser')
            new_captcha = await _detect_captcha_on_page(page, new_soup)
            
            if not new_captcha:
                print("  ✅ CAPTCHA solved successfully!")
                return True
            else:
                print("  ⚠️  CAPTCHA still present, retrying...")
        
        await page.wait_for_timeout(3000)
    
    print("  ❌ Failed to solve CAPTCHA within timeout")
    return False


async def _detect_captcha_on_page(page, soup) -> Optional[Dict]:
    """Detect CAPTCHA type and extract sitekey"""
    
    # Check for reCAPTCHA
    recaptcha_elem = soup.find(attrs={'data-sitekey': True, 'class': re.compile(r'g-recaptcha', re.I)})
    if not recaptcha_elem:
        recaptcha_elem = soup.find('div', class_=re.compile(r'g-recaptcha', re.I))
    if not recaptcha_elem:
        # Check for reCAPTCHA v3 (invisible)
        recaptcha_script = soup.find('script', src=re.compile(r'recaptcha/api\.js'))
        if recaptcha_script:
            # Try to find sitekey in page source
            page_source = str(soup)
            sitekey_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_source)
            if sitekey_match:
                return {'type': 'recaptcha', 'sitekey': sitekey_match.group(1)}
    
    if recaptcha_elem and recaptcha_elem.get('data-sitekey'):
        return {'type': 'recaptcha', 'sitekey': recaptcha_elem['data-sitekey']}
    
    # Check for hCaptcha
    hcaptcha_elem = soup.find(attrs={'data-sitekey': True, 'class': re.compile(r'h-captcha', re.I)})
    if not hcaptcha_elem:
        hcaptcha_elem = soup.find('div', class_=re.compile(r'h-captcha', re.I))
    if not hcaptcha_elem:
        # Check for generic CAPTCHA iframes
        captcha_iframes = soup.find_all('iframe', src=re.compile(r'captcha|recaptcha|hcaptcha|turnstile', re.I))
        if captcha_iframes:
            # Try to extract sitekey from iframe src
            for iframe in captcha_iframes:
                src = iframe.get('src', '')
                sitekey_match = re.search(r'[?&]k=([^&]+)', src)
                if sitekey_match:
                    if 'recaptcha' in src.lower():
                        return {'type': 'recaptcha', 'sitekey': sitekey_match.group(1)}
                    elif 'hcaptcha' in src.lower():
                        return {'type': 'hcaptcha', 'sitekey': sitekey_match.group(1)}
                    elif 'turnstile' in src.lower():
                        return {'type': 'turnstile', 'sitekey': sitekey_match.group(1)}
    
    return None


async def solve_captcha_nopecha(api_key: str, sitekey: str, page_url: str, captcha_type: str) -> Optional[str]:
    """Solve CAPTCHA using NopeCHA API (free tier available)"""
    try:
        async with aiohttp.ClientSession() as session:
            # Create task
            task_data = {
                'type': captcha_type,
                'sitekey': sitekey,
                'url': page_url,
                'key': api_key
            }
            
            async with session.post(f"{NOPECHA_API_URL}/", json=task_data, timeout=30) as resp:
                if resp.status != 200:
                    print(f"    NopeCHA error: {resp.status}")
                    return None
                
                result = await resp.json()
                task_id = result.get('data')
                
                if not task_id:
                    print(f"    NopeCHA failed to create task: {result}")
                    return None
                
                # Poll for solution
                for _ in range(24):  # 2 minutes max
                    await asyncio.sleep(5)
                    
                    async with session.get(f"{NOPECHA_API_URL}/?key={api_key}&id={task_id}", timeout=30) as check_resp:
                        if check_resp.status == 200:
                            check_result = await check_resp.json()
                            
                            if check_result.get('data'):
                                return check_result['data']
                            
                            if check_result.get('error'):
                                print(f"    NopeCHA error: {check_result['error']}")
                                return None
                
                print("    NopeCHA timeout")
                return None
                
    except Exception as e:
        print(f"    NopeCHA exception: {e}")
        return None


async def solve_captcha_anticaptcha(api_key: str, sitekey: str, page_url: str, captcha_type: str) -> Optional[str]:
    """Solve CAPTCHA using Anti-Captcha API"""
    try:
        async with aiohttp.ClientSession() as session:
            # Map captcha type to Anti-Captcha task type
            task_type_map = {
                'recaptcha': 'RecaptchaV2TaskProxyless',
                'hcaptcha': 'HCaptchaTaskProxyless',
                'turnstile': 'TurnstileTaskProxyless'
            }
            
            task_type = task_type_map.get(captcha_type, 'RecaptchaV2TaskProxyless')
            
            # Create task
            task_data = {
                'clientKey': api_key,
                'task': {
                    'type': task_type,
                    'websiteURL': page_url,
                    'websiteKey': sitekey
                }
            }
            
            async with session.post(f"{ANTICAPTCHA_API_URL}/createTask", json=task_data, timeout=30) as resp:
                if resp.status != 200:
                    return None
                
                result = await resp.json()
                task_id = result.get('taskId')
                
                if not task_id:
                    print(f"    Anti-Captcha error: {result.get('errorDescription')}")
                    return None
                
                # Poll for solution
                for _ in range(24):
                    await asyncio.sleep(5)
                    
                    check_data = {
                        'clientKey': api_key,
                        'taskId': task_id
                    }
                    
                    async with session.post(f"{ANTICAPTCHA_API_URL}/getTaskResult", json=check_data, timeout=30) as check_resp:
                        if check_resp.status == 200:
                            check_result = await check_resp.json()
                            
                            if check_result.get('status') == 'ready':
                                return check_result.get('solution', {}).get('gRecaptchaResponse')
                            
                            if check_result.get('errorId'):
                                print(f"    Anti-Captcha error: {check_result.get('errorDescription')}")
                                return None
                
                return None
                
    except Exception as e:
        print(f"    Anti-Captcha exception: {e}")
        return None


async def attempt_captcha_bypass(page, captcha_type: str) -> bool:
    """
    Attempt to bypass CAPTCHA using automated techniques
    This includes hiding CAPTCHA elements and simulating completion
    """
    try:
        print("    Attempting automated bypass techniques...")
        
        # Technique 1: Hide CAPTCHA elements
        await page.evaluate("""
            () => {
                // Hide all CAPTCHA iframes
                document.querySelectorAll('iframe[src*="captcha"], iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="turnstile"]').forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.opacity = '0';
                });
                
                // Hide CAPTCHA containers
                document.querySelectorAll('[class*="captcha"], [class*="recaptcha"], [class*="hcaptcha"], [class*="turnstile"]').forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.opacity = '0';
                });
            }
        """)
        
        await page.wait_for_timeout(2000)
        
        # Technique 2: Try to trigger form submission
        try:
            # Look for submit buttons
            if hasattr(page, 'query_selector_all'):
                submit_buttons = await page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("Continue"), button:has-text("Submit")')
                for button in submit_buttons:
                    if button and await button.is_visible():
                        await button.click()
                        if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                            await page.wait_for_timeout(2000)
                        else:  # For pydoll Tab objects
                            await asyncio.sleep(2.0)
                        break
            else:
                # For pydoll Tab objects, use execute_script to find and click submit buttons
                submit_clicked = await page.execute_script('''
                    const submitButtons = document.querySelectorAll('button[type="submit"], input[type="submit"], button:has-text("Continue"), button:has-text("Submit")');
                    if (submitButtons.length > 0) {
                        submitButtons[0].click();
                        console.log("Clicked submit button");
                        return true;
                    }
                    return false;
                ''')
                if submit_clicked:
                    if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                        await page.wait_for_timeout(2000)
                    else:  # For pydoll Tab objects
                        await asyncio.sleep(2.0)
        except:
            pass
        
        # Technique 3: Simulate CAPTCHA completion
        await page.evaluate(f"""
            () => {{
                // Set response tokens
                const responseFields = document.querySelectorAll('textarea[name="g-recaptcha-response"], textarea[name="h-captcha-response"], textarea[name="cf-turnstile-response"]');
                responseFields.forEach(field => {{
                    field.value = 'bypass_attempt_{random.randint(1000, 9999)}';
                    field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }});
                
                // Trigger callback if exists
                if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {{
                    try {{
                        const response = grecaptcha.getResponse();
                        if (window.onCaptchaSuccess) {{
                            window.onCaptchaSuccess(response);
                        }}
                    }} catch(e) {{}}
                }}
            }}
        """)
        
        await page.wait_for_timeout(2000)
        
        # Check if bypass worked
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        captcha_still_present = await _detect_captcha_on_page(page, soup)
        
        return captcha_still_present is None
        
    except Exception as e:
        print(f"    Bypass attempt failed: {e}")
        return False


def _determine_captcha_type(widget) -> str:
    attr_values = ' '.join([str(v) for v in widget.attrs.values() if v])
    lowered = attr_values.lower()
    if 'hcaptcha' in lowered:
        return 'hcaptcha'
    if 'turnstile' in lowered or 'cf-turnstile' in lowered:
        return 'turnstile'
    return 'recaptcha'


async def _inject_captcha_solution(page, solution: str, captcha_type: str):
    field_name = {
        'recaptcha': 'g-recaptcha-response',
        'hcaptcha': 'h-captcha-response',
        'turnstile': 'cf-turnstile-response',
    }.get(captcha_type, 'g-recaptcha-response')

    escaped_solution = json.dumps(solution)
    script = f"""
        (() => {{
            const field = document.querySelector('textarea[name="{field_name}"]');
            if (!field) return;
            field.value = {escaped_solution};
            field.dispatchEvent(new Event('input', {{ bubbles: true }}));
            field.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})();
    """
    await page.evaluate(script)
    await page.wait_for_timeout(1000)


def request_captcha_solution(api_key: str, site_key: str, page_url: str, captcha_type: str, timeout: int = CAPTCHA_POLL_TIMEOUT) -> Optional[str]:
    method = CAPTCHA_METHODS.get(captcha_type, 'userrecaptcha')
    payload = {
        'key': api_key,
        'method': method,
        'googlekey': site_key,
        'pageurl': page_url,
        'json': 1,
    }

    try:
        resp = requests.post(f"{CAPTCHA_SOLVER_BASE_URL}/in.php", data=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get('status') != 1:
            print(f"Captcha request failed: {data.get('request')}")
            return None

        captcha_id = data.get('request')
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            time.sleep(CAPTCHA_POLL_INTERVAL)
            check_resp = requests.get(
                f"{CAPTCHA_SOLVER_BASE_URL}/res.php",
                params={'key': api_key, 'action': 'get', 'id': captcha_id, 'json': 1},
                timeout=30
            )
            check_resp.raise_for_status()
            check_data = check_resp.json()

            if check_data.get('status') == 1:
                return check_data.get('request')

            if check_data.get('request') not in ('CAPTCHA_NOT_READY', 'CAPTCHA_NOT_READY'):
                print(f"Captcha solver error: {check_data.get('request')}")
                return None

        print("Captcha solution timed out")
        return None

    except requests.RequestException as exc:
        print(f"Captcha solver network error: {exc}")
        return None


def extract_captcha_from_snapshot(snapshot_text: str) -> Optional[Dict[str, str]]:
    match = re.search(r'data-sitekey=["\']([^"\']+)["\']', snapshot_text)
    if not match:
        match = re.search(r'sitekey=([^&\s]+)', snapshot_text)
    if not match:
        return None

    snippet = snapshot_text[max(0, match.start() - 80):match.end() + 80].lower()
    captcha_type = 'hcaptcha' if 'hcaptcha' in snippet else 'turnstile' if 'turnstile' in snippet or 'cf-turnstile' in snippet else 'recaptcha'

    return {'sitekey': match.group(1), 'captcha_type': captcha_type}


async def solve_captcha_from_snapshot(snapshot_text: str, page_url: str) -> Optional[str]:
    details = extract_captcha_from_snapshot(snapshot_text)
    if not details:
        return None

    solver_key = os.environ.get("CAPTCHA_SOLVER_API_KEY") or os.environ.get("CAPTCHA_API_KEY")
    if not solver_key:
        print("Captcha solver API key is not set; skipping automated solve")
        return None

    return await asyncio.to_thread(
        request_captcha_solution,
        solver_key,
        details['sitekey'],
        page_url,
        details['captcha_type'],
        CAPTCHA_POLL_TIMEOUT,
    )