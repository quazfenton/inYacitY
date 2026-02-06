# Scraper Fix & Troubleshooting Guide

## Issue Summary

The scrapers (Eventbrite, Meetup, Luma) were not working because:
1. **Old `run.py`** only imported Meetup and Luma (Eventbrite was missing)
2. **All 3 scrapers are in `scrapeevents.py`** (consolidated location)
3. **Run.py needed to be rewritten** to call the correct functions

## What Was Fixed

### ✅ New `run.py` 
Complete rewrite that:
- Imports all 3 scrapers from `scrapeevents.py`
- Properly handles location format conversion for each source
- Merges results from all 3 sources
- Saves to `all_events.json` with proper structure
- Includes Eventbrite scraping (was missing!)

### ✅ New `test_all_scrapers.py`
Diagnostic script to test each scraper individually:
- Tests Eventbrite with real URL
- Tests Meetup with real location code
- Tests Luma with real city code
- Shows sample output for each
- Clear PASS/FAIL status

## How to Test

### Step 1: Run Diagnostics

```bash
cd /home/workspace/inyAcity/scraper

# Test each scraper individually
python test_all_scrapers.py
```

Expected output:
```
TESTING EVENTBRITE SCRAPER
Testing URL: https://www.eventbrite.com/d/ca--los-angeles/free--events/?page=1
✓ Eventbrite scraper working!
  Found 25 events

TESTING MEETUP SCRAPER
Testing location: us--ca--los-angeles
✓ Meetup scraper working!
  Found 15 events

TESTING LUMA SCRAPER
Testing city: la
✓ Luma scraper working!
  Found 8 events

SUMMARY
eventbrite     ✓ PASS
meetup         ✓ PASS
luma           ✓ PASS

Overall        ✓ ALL PASS
```

### Step 2: Run Full Scraper

```bash
# Set location in config.json first
# Then run full scraper
python run.py
```

Expected output:
```
EVENT SCRAPER - Eventbrite + Meetup + Luma (COMPLETE VERSION)
Location: ca--los-angeles

[1/3] Scraping Eventbrite for ca--los-angeles...
  Scraping: https://www.eventbrite.com/d/ca--los-angeles/free--events/?page=1
  Found 25 events on this page
✓ Eventbrite total: 25 events

[2/3] Scraping Meetup for ca--los-angeles...
✓ Meetup total: 15 events

[3/3] Scraping Luma for ca--los-angeles...
✓ Luma total: 8 events

[4/4] Merging results...
✓ Merged 48 unique events
✓ Saved to all_events.json

SUMMARY
  Eventbrite events: 25
  Meetup events: 15
  Luma events: 8
  Total unique: 48
```

## Configuration

### Update Location

Edit `scraper/config.json`:

```json
{
  "LOCATION": "ca--los-angeles",  // Change this
  "MODES": {
    "ENABLE_EVENTBRITE_SCRAPING": true,
    "ENABLE_MEETUP_SCRAPING": true,
    "ENABLE_LUMA_SCRAPING": true
  }
}
```

**Supported locations** (from config.json):
```
ca--los-angeles
ny--new-york
ca--san-francisco
il--chicago
tx--austin
fl--miami
dc--washington
co--denver
tx--dallas
wa--seattle
ma--boston
ga--atlanta
or--portland
az--phoenix
tx--houston
nv--las-vegas
mi--detroit
nc--charlotte
tn--nashville
pa--philadelphia
(and 20+ more)
```

### Disable Specific Sources

If a source is failing, you can disable it:

```json
{
  "MODES": {
    "ENABLE_EVENTBRITE_SCRAPING": false,  // Disable Eventbrite
    "ENABLE_MEETUP_SCRAPING": true,       // Keep Meetup
    "ENABLE_LUMA_SCRAPING": true          // Keep Luma
  }
}
```

## Troubleshooting

### Issue: Eventbrite Returns 0 Events

**Causes:**
- Website structure changed (Eventbrite updates frequently)
- Location format is incorrect
- Network issue or CloudFlare block

**Solutions:**

1. Check location format in config:
```bash
# Should be like: ca--los-angeles
grep "LOCATION" scraper/config.json
```

2. Check if Eventbrite is blocking:
```python
# Run debug script
python debug_eventbrite.py
```

3. Verify HTML structure hasn't changed:
```bash
# Check the generated HTML
ls -la debug_*.html
```

4. Try with Firecrawl fallback (if configured):
```json
{
  "FALLBACKS": {
    "ENABLE_FIRECRAWL_FALLBACK": true,
    "ENABLE_HYPERBROWSER_FALLBACK": true
  }
}
```

### Issue: Meetup Returns 0 Events

**Causes:**
- Location format must be: `us--{state}--{city}`
- Meetup may have limited events in that city
- Browser automation detection

**Solution:**

Verify location format conversion in `run.py`:
```python
# Should convert ca--los-angeles to us--ca--los-angeles
parts = location.split('--')
meetup_location = f"us--{parts[0]}--{parts[1]}"
```

### Issue: Luma Returns 0 Events

**Causes:**
- City code must match Luma's supported cities
- Luma is primarily for NYC, LA, SF, DC

**Solution:**

Check city mapping in `run.py`:
```python
location_to_luma = {
    'dc--washington': 'dc',
    'ny--new-york': 'nyc',
    'ca--los-angeles': 'la',
    'ca--san-francisco': 'sf',
    # ... etc
}
```

If your city isn't listed, add it to the mapping.

### Issue: All Scrapers Return 0 Events

**Causes:**
1. Network/internet connectivity issue
2. All three sources blocking simultaneously (unlikely)
3. Browser/Playwright issue

**Solutions:**

1. Check internet connection:
```bash
ping google.com
```

2. Check Playwright is installed:
```bash
python -c "from playwright.async_api import async_playwright; print('Playwright OK')"
```

3. Check browser binaries are installed:
```bash
playwright install chromium
```

4. Check for CloudFlare blocks:
```bash
# Try accessing directly
curl https://www.eventbrite.com/d/ca--los-angeles/free--events/ -I
```

5. Clear old data and retry:
```bash
rm all_events.json meetup_events.json luma_events.json
python run.py
```

## Integration with Backend

### Backend Scraper Endpoint

When backend calls `/scrape/{city_id}`:

```python
# backend/scraper_integration.py
await scrape_city_events(city_id)
```

This should now:
1. Call `run.py` with location set to `city_id`
2. Scraper runs all 3 sources
3. Saves to `all_events.json`
4. Backend reads and stores in database

### Verify Backend Integration

```bash
# Test backend scraper endpoint
curl -X POST http://localhost:8000/scrape/ca--los-angeles

# Response should be:
{
  "status": "success",
  "events_scraped": 48,
  "events_saved": 48,
  "events_updated": 0
}
```

## Performance Tuning

### Reduce Execution Time

If scraping is slow, disable unused sources:

```json
{
  "MODES": {
    "ENABLE_EVENTBRITE_SCRAPING": true,  // Only use fast source
    "ENABLE_MEETUP_SCRAPING": false,     // Disable slow ones
    "ENABLE_LUMA_SCRAPING": false
  }
}
```

### Reduce Event Limit

Edit `config.json`:

```json
{
  "MAIN_PAGES": 1,  // Only first page (was 2)
  "MAX_EVENTS_PER_PAGE": 30
}
```

### Increase Timeout (For Slow Networks)

Edit `scrapeevents.py` and increase wait times:

```python
await page.goto(url, wait_until="domcontentloaded", timeout=30000)  # 30 seconds
```

## Monitoring

### View Execution Logs

When scraper runs:

```bash
# Check if all_events.json was created
ls -la all_events.json

# Check event count
python -c "import json; data=json.load(open('all_events.json')); print(f\"Total events: {data['total']}\")"

# Check last update time
python -c "import json; data=json.load(open('all_events.json')); print(f\"Last updated: {data['last_updated']}\")"
```

### Debug Individual Scrapers

```bash
# Debug Eventbrite
python -c "
import asyncio
from scrapeevents import scrape_eventbrite_page
events = asyncio.run(scrape_eventbrite_page('https://www.eventbrite.com/d/ca--los-angeles/free--events/?page=1'))
print(f'Found {len(events)} Eventbrite events')
"

# Debug Meetup
python -c "
import asyncio
from scrapeevents import scrape_meetup_events
events = asyncio.run(scrape_meetup_events('us--ca--los-angeles'))
print(f'Found {len(events)} Meetup events')
"

# Debug Luma
python -c "
import asyncio
from scrapeevents import scrape_luma_events
events = asyncio.run(scrape_luma_events('la'))
print(f'Found {len(events)} Luma events')
"
```

## Key Files

| File | Purpose |
|------|---------|
| `run.py` | Main scraper orchestrator (FIXED) |
| `test_all_scrapers.py` | Diagnostic test script (NEW) |
| `scrapeevents.py` | All 3 scrapers (Eventbrite, Meetup, Luma) |
| `config.json` | Configuration (location, sources, etc) |
| `all_events.json` | Output with merged events |

## Next Steps

1. **Test**: Run `python test_all_scrapers.py`
2. **Verify**: Check `all_events.json` has events
3. **Integrate**: Confirm backend can call scraper
4. **Monitor**: Check daily scrapes are working
5. **Tune**: Optimize if needed

## Still Not Working?

If scrapers still aren't working:

1. Check browser is installed:
```bash
playwright install chromium
```

2. Check dependencies:
```bash
pip install -r requirements.txt
```

3. Check for network issues:
```bash
ping eventbrite.com
ping meetup.com
ping luma.com
```

4. Try with debug mode:
```bash
DEBUG=* python run.py
```

5. Check CloudFlare status:
- Visit https://www.eventbrite.com manually
- If blocked, use Firecrawl/Hyperbrowser fallback
- Set API keys in .env

---

**Status**: ✅ Fixed and Ready to Test  
**Date**: February 5, 2026
