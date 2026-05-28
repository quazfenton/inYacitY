#!/usr/bin/env python3
"""Test pydoll + scroll + parser integration."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(__file__))

os.environ['FIRECRAWL_API_KEY'] = ''
os.environ['HYPERBROWSER_API_KEY'] = ''
os.environ['BROWSERBASE_API_KEY'] = ''
os.environ['ANCHOR_BROWSER_API_KEY'] = ''

async def test():
    print("=== pydoll + scroll + parser ===\n")
    try:
        from pydoll.browser import Chrome as PydollChrome
        from pydoll.browser.options import ChromiumOptions
        from browser import chromium_args, dismiss_overlays, scroll_page
        from facebook_scraper import parse_events_from_html

        options = ChromiumOptions()
        for arg in chromium_args():
            options.add_argument(arg)
        options.add_argument('--ignore-certificate-errors')
        options.headless = True
        options.start_timeout = 30

        print("Creating pydoll browser...")
        p_browser = PydollChrome(options=options)
        page = await p_browser.start()
        await page.enable_auto_solve_cloudflare_captcha()

        url = "https://www.facebook.com/events/search/?q=this+week&location=new+york"
        print(f"Navigating to Facebook events...")
        await page.go_to(url)
        await asyncio.sleep(5)

        # Phase 1: raw HTML before any modification
        raw_html = await page.page_source
        raw_events = parse_events_from_html(raw_html)
        print(f"\n[Phase 1] Before dismiss/scroll: {len(raw_events)} events")

        # Phase 2: dismiss overlays
        print("\nDismissing overlays...")
        await dismiss_overlays(page)
        await asyncio.sleep(1)

        dismissed_html = await page.page_source
        dismissed_events = parse_events_from_html(dismissed_html)
        print(f"[Phase 2] After dismiss: {len(dismissed_events)} events")

        # Phase 3: scroll to load more
        print("\nScrolling to load more events...")
        scrolls = await scroll_page(page, max_scrolls=20, scroll_pause=2.0)

        scrolled_html = await page.page_source
        scrolled_events = parse_events_from_html(scrolled_html)
        print(f"\n[Phase 3] After {scrolls} scrolls: {len(scrolled_events)} events (HTML: {len(scrolled_html)} chars)")

        # Print all events
        if scrolled_events:
            print(f"\nAll {len(scrolled_events)} events:")
            for i, e in enumerate(scrolled_events):
                title = e['title'][:60]
                date = e['date'] or 'No date'
                loc = e['location'][:40]
                print(f"  {i+1}. {title} | {date} | {loc}")
        else:
            print("\nNo events parsed. Checking HTML for /events/ links...")
            import re
            links = re.findall(r'href="(/events/\d+[^"]*)"', scrolled_html)
            print(f"  Event link hrefs found: {len(links)}")
            for l in links[:5]:
                print(f"    {l[:80]}")

        await p_browser.stop()
        print("\n=== Done ===")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
