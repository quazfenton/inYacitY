#!/usr/bin/env python3
"""
Debug script to examine Eventbrite HTML structure
"""

from playwright.async_api import async_playwright
import asyncio

async def debug_eventbrite_structure():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Changed from True to False to avoid detection
        page = await browser.new_page()
        
        try:
            print("Accessing Eventbrite page...")
            await page.goto("https://www.eventbrite.com/d/dc--washington/free--events/?page=1", wait_until="networkidle")
            
            # Wait a bit more for dynamic content
            if hasattr(page, 'wait_for_timeout'):  # For Playwright-based browsers
                await page.wait_for_timeout(5000)
            else:  # For pydoll Tab objects
                await asyncio.sleep(5.0)
            
            # Get the full HTML content
            if hasattr(page, 'content'):  # For Playwright-based browsers
                content = await page.content()
            else:  # For pydoll Tab objects
                result = await page.execute_script("return document.documentElement.outerHTML")
                # Handle potential dict response from pydoll
                if isinstance(result, dict) and 'result' in result:
                    content = result['result']
                elif isinstance(result, dict) and 'value' in result:
                    content = result['value']
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result) if result is not None else ""

            # Save to file for inspection
            with open("/home/workspace/Events/eventbrite_debug.html", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("HTML content saved to /home/workspace/Events/eventbrite_debug.html")
            
            # Look for common event-related selectors
            print("\nLooking for common selectors...")
            
            # Count elements with common attributes
            selectors_to_try = [
                '[data-testid*="event"]',
                '[data-testid*="card"]',
                '[data-testid*="listing"]',
                '.event-card',
                '.listing-card',
                'article',
                'a[href*="/e/"]',
                'a[href*="/event/"]',
                '[href*="/e/"]',
                '[href*="/event/"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    count = await page.evaluate(f'document.querySelectorAll("{selector}").length')
                    print(f"Selector '{selector}' found {count} elements")
                except:
                    print(f"Selector '{selector}' failed")
        
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_eventbrite_structure())