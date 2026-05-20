#!/usr/bin/env python3
"""
Simple browser setup - no fancy anti-detection that causes more problems
"""

from playwright.async_api import async_playwright


async def create_browser(headless=True):
    """Create a simple browser without over-engineered stealth"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=headless,
        args=['--no-sandbox']
    )
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    page = await context.new_page()
    # Store playwright to prevent GC
    browser._playwright = playwright
    return browser, page


async def close_browser(browser):
    """Close browser properly"""
    if browser:
        await browser.close()
        if hasattr(browser, '_playwright'):
            await browser._playwright.stop()
