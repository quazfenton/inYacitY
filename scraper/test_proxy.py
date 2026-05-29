#!/usr/bin/env python3
import asyncio, sys
sys.path.insert(0, '/app/scraper')

async def main():
    print("Starting...", flush=True)
    from proxy_fallback import get_prewarmed_proxies, fetch_with_proxy
    proxies = await get_prewarmed_proxies(force_refresh=True)
    print(f'HTTPS-capable: {len(proxies)}', flush=True)
    if not proxies:
        return
    
    for i, p in enumerate(proxies[:8]):
        print(f'  Testing #{i+1}: {p.split("://")[0]}://...{p[-10:]}', flush=True)
        html = await fetch_with_proxy('https://ra.co/events/us/losangeles', p, timeout=15)
        if html:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('h3', attrs={'data-pw-test-id': 'event-title'})
            if not titles:
                titles = soup.select('h3[class*="EventTitle"]')
            print(f'  #{i+1}: {len(html)}b, {len(titles)} events', flush=True)
            if titles:
                break
        else:
            print(f'  #{i+1}: FAIL', flush=True)

asyncio.run(main())
