# API Fallback Setup Guide

## Quick Start

The event scraper now includes automatic fallback to cloud browser APIs when Playwright encounters anti-bot detection or timeouts.

---

## Option 1: Browserbase (Recommended)

### Why Browserbase?
- ✅ Best for JavaScript-heavy sites (Meetup, Luma use React)
- ✅ Includes automatic scrolling and content loading
- ✅ Excellent for dynamic content
- ✅ Reliable uptime and support

### Setup Steps

**1. Create Browserbase Account**
```
Visit: https://browserbase.com
Sign up for free tier (includes 5000 API calls/month)
```

**2. Get API Key**
- Log in to dashboard
- Navigate to Settings → API Keys
- Copy your API key

**3. Configure Environment Variable**
```bash
# Add to ~/.bashrc or ~/.zshrc
export BROWSERBASE_API_KEY="your_key_here"

# Or set temporarily in shell
export BROWSERBASE_API_KEY="pk_live_abc123..."

# Verify it's set
echo $BROWSERBASE_API_KEY
```

**4. Test the Integration**
```python
import asyncio
import os
from scraper.scrapeevents import scrape_with_browserbase

async def test():
    html = await scrape_with_browserbase("https://www.meetup.com/find/?location=us--ny--new-york")
    if html:
        print("✓ Browserbase working!")
        print(f"  Got {len(html)} bytes of HTML")
    else:
        print("✗ Browserbase failed - check API key")

asyncio.run(test())
```

### API Documentation
- **Official Docs:** https://docs.browserbase.com
- **API Reference:** https://docs.browserbase.com/api
- **Python SDK:** `pip install browserbase`

### Pricing
- **Free tier:** 5,000 requests/month
- **Pro tier:** 100,000 requests/month ($29/month)
- **Enterprise:** Custom pricing

---

## Option 2: AnchorBrowser

### Why AnchorBrowser?
- ✅ Very fast page rendering
- ✅ Minimal overhead
- ✅ Good for simple HTML extraction
- ✅ Lower latency than Browserbase

### Setup Steps

**1. Create AnchorBrowser Account**
```
Visit: https://www.anchorbrowser.io
Sign up (free tier available)
```

**2. Get API Key**
- Log in to dashboard
- Go to API Keys section
- Generate and copy your key

**3. Configure Environment Variable**
```bash
export ANCHOR_BROWSER_API_KEY="your_key_here"

# Verify
echo $ANCHOR_BROWSER_API_KEY
```

**4. Test the Integration**
```python
import asyncio
from scraper.scrapeevents import scrape_with_anchor_browser

async def test():
    html = await scrape_with_anchor_browser("https://luma.com/houston")
    if html:
        print("✓ AnchorBrowser working!")
        print(f"  Got {len(html)} bytes of HTML")
    else:
        print("✗ AnchorBrowser failed - check API key")

asyncio.run(test())
```

### API Documentation
- **Official Docs:** https://www.anchorbrowser.io/docs
- **Pricing:** https://www.anchorbrowser.io/pricing

### Pricing
- **Free tier:** 1,000 requests/month
- **Starter:** 10,000 requests/month ($9/month)
- **Pro:** 100,000 requests/month ($49/month)

---

## Option 3: Using Both (Recommended Setup)

Set both APIs and let the fallback chain try them in order:

```bash
# Set both keys
export BROWSERBASE_API_KEY="your_browserbase_key"
export ANCHOR_BROWSER_API_KEY="your_anchor_key"
```

The scraper will try:
1. Playwright (local browser) - fastest, no cost
2. Browserbase - if Playwright fails
3. AnchorBrowser - if Browserbase fails

```python
# Automatic fallback chain
from scraper.scrapeevents import scrape_with_api_fallback

html = await scrape_with_api_fallback(
    url,
    fallback_order=["browserbase", "anchor_browser"]
)
```

---

## Environment Variable Persistence

### Option A: Shell Configuration Files

**For bash users:**
```bash
# Add to ~/.bashrc
echo 'export BROWSERBASE_API_KEY="your_key"' >> ~/.bashrc
echo 'export ANCHOR_BROWSER_API_KEY="your_key"' >> ~/.bashrc
source ~/.bashrc
```

**For zsh users:**
```bash
echo 'export BROWSERBASE_API_KEY="your_key"' >> ~/.zshrc
echo 'export ANCHOR_BROWSER_API_KEY="your_key"' >> ~/.zshrc
source ~/.zshrc
```

### Option B: .env File (Recommended for Projects)

**Create `.env` file:**
```
BROWSERBASE_API_KEY=your_key_here
ANCHOR_BROWSER_API_KEY=your_key_here
```

**Load in Python:**
```python
from dotenv import load_dotenv
import os

load_dotenv()
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
ANCHOR_BROWSER_API_KEY = os.getenv("ANCHOR_BROWSER_API_KEY")
```

**Install dotenv:**
```bash
pip install python-dotenv
```

### Option C: Zo Computer Settings (Recommended for Zo)

Store API keys securely in Zo settings:

1. Go to [Settings > Developers](/?t=settings&s=developers)
2. Add secrets:
   - **Name:** `BROWSERBASE_API_KEY`
   - **Value:** Your key from browserbase.com
   - Repeat for `ANCHOR_BROWSER_API_KEY`

These will be automatically available to scripts via `os.environ`.

---

## Testing Your Setup

### Full Integration Test

```python
import asyncio
import os
from scraper.scrapeevents import scrape_with_api_fallback

async def test_all():
    print("Testing Event Scraper Setup\n")

    # Check API keys
    print("1. Checking API keys...")
    browserbase = bool(os.getenv("BROWSERBASE_API_KEY"))
    anchor = bool(os.getenv("ANCHOR_BROWSER_API_KEY"))
    print(f"   Browserbase configured: {browserbase}")
    print(f"   AnchorBrowser configured: {anchor}\n")

    # Test API fallback
    print("2. Testing API fallback...")
    try:
        html = await scrape_with_api_fallback("https://example.com")
        if html:
            print(f"   ✓ API fallback working ({len(html)} bytes)\n")
        else:
            print(f"   ✗ API fallback returned no content\n")
    except Exception as e:
        print(f"   ✗ API fallback failed: {e}\n")

    print("Setup test complete!")

asyncio.run(test_all())
```

---

## Troubleshooting

### "API key not configured" Error

**Problem:** Script says API key is not set

**Solution:**
```bash
# Check if key is actually set
echo $BROWSERBASE_API_KEY

# If empty, set it
export BROWSERBASE_API_KEY="your_actual_key"

# Verify
echo $BROWSERBASE_API_KEY
# Should print your key
```

### "Invalid API key" or 401 Unauthorized

**Problem:** API returns 401 error

**Solutions:**
1. Double-check you're using the correct key (copy from dashboard again)
2. Ensure the key hasn't been revoked in the service dashboard
3. Check if the key has API permissions enabled
4. For Browserbase: Verify you're using `Bearer {key}` format (handled automatically)
5. For AnchorBrowser: Check API key format in their docs

### Timeout Issues

**Problem:** Script hangs or times out

**Solutions:**
```python
# Increase timeout in scraper
# In accurate_scrape_dc_events_v2.py, change:
timeout=aiohttp.ClientTimeout(total=120)  # Instead of 60
```

### Too Many Requests

**Problem:** 429 (Rate Limited) error

**Solutions:**
1. You've exceeded your API tier limits
2. Upgrade to higher tier plan
3. Implement request caching/deduplication
4. Add delays between requests:
   ```python
   await asyncio.sleep(1)  # Wait 1 second between requests
   ```

---

## Switching Between APIs

### Use Only Browserbase
```python
html = await scrape_with_browserbase(url)
```

### Use Only AnchorBrowser
```python
html = await scrape_with_anchor_browser(url)
```

### Custom Fallback Order
```python
html = await scrape_with_api_fallback(
    url,
    fallback_order=["anchor_browser", "browserbase"]  # Try Anchor first
)
```

### Disable API Fallbacks (Playwright Only)
```python
# In main scraper functions, remove the except block
# that calls scrape_with_api_fallback
```

---

## Cost Estimation

For scraping 100 events/day:

**Browserbase:**
- 100 events × 30 days = 3,000 requests/month
- **Free tier:** Covers all 3,000 ✓

**AnchorBrowser:**
- Same as above
- **Free tier:** 1,000 requests/month (need Starter plan)
- **Starter plan:** $9/month covers 10,000 requests ✓

**Recommended:** Browserbase free tier handles most use cases.

---

## Production Checklist

- [ ] API keys set in environment variables
- [ ] Both Browserbase and AnchorBrowser configured
- [ ] Tested fallback chain with `test_all()` script
- [ ] Verified events are being scraped correctly
- [ ] Logged into [Zo Settings](/?t=settings&s=developers) and added secrets
- [ ] Script runs without errors for 5+ minutes
- [ ] Check API dashboards for usage/limits

---

## Next Steps

1. **Choose an API**: Browserbase (recommended) or both
2. **Get your API key**: Visit their dashboard
3. **Set environment variable**: Add to ~/.bashrc or Zo Settings
4. **Run test script**: Verify it's working
5. **Enable in scraper**: Both APIs are already integrated!

For questions about specific APIs, visit:
- Browserbase: https://browserbase.com/docs
- AnchorBrowser: https://www.anchorbrowser.io/docs

