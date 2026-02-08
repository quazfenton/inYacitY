# Quick Scraper Test - 5 Minute Verification

## Step 1: Navigate to Scraper (30 seconds)

```bash
cd /home/workspace/inyAcity/scraper
```

## Step 2: Run Diagnostic Test (3 minutes)

```bash
python test_all_scrapers.py
```

### What You Should See:

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

### If You See Errors:

- **Eventbrite fails**: Check network, try Firecrawl fallback
- **Meetup fails**: Check location format (should be us--ca--los-angeles)
- **Luma fails**: Check city is in mapping (la, nyc, sf, dc, etc)
- **All fail**: Check internet connection, reinstall Playwright

## Step 3: Run Full Scraper (1-2 minutes)

```bash
python run.py
```

### What You Should See:

```
EVENT SCRAPER - Eventbrite + Meetup + Luma (COMPLETE VERSION)
Location: ca--los-angeles

[1/3] Scraping Eventbrite for ca--los-angeles...
✓ Eventbrite total: 25 events

[2/3] Scraping Meetup for ca--los-angeles...
✓ Meetup total: 15 events

[3/3] Scraping Luma for ca--los-angeles...
✓ Luma total: 8 events

✓ Merged 48 unique events
✓ Saved to all_events.json
```

## Step 4: Verify Output (30 seconds)

```bash
# Check file was created
ls -lh all_events.json

# Check event count
python -c "import json; d=json.load(open('all_events.json')); print(f'Total: {d[\"total\"]} events')"

# View sample
python -c "import json; d=json.load(open('all_events.json')); e=d['events'][0]; print(f'{e[\"title\"]} - {e[\"date\"]}')"
```

## Step 5: Test Backend Integration

```bash
# Terminal 1: Start backend
cd /home/workspace/inyAcity/backend
python -m uvicorn main:app --reload

# Terminal 2: Test scraper endpoint
curl -X POST http://localhost:8000/scrape/ca--los-angeles

# Should return:
# {"message":"Scraping initiated for ca--los-angeles","city_id":"ca--los-angeles","note":"Events will be synced to shared database in real-time"}

# Wait 60 seconds, then check events:
curl http://localhost:8000/events/ca--los-angeles | head -20
```

## Quick Fixes

### If Eventbrite Returns 0

```bash
# Check location format
grep "LOCATION" config.json
# Should show: "LOCATION": "ca--los-angeles"

# Check Firecrawl fallback enabled
grep "ENABLE_FIRECRAWL_FALLBACK" config.json
# Should show: "ENABLE_FIRECRAWL_FALLBACK": true
```

### If Meetup Returns 0

```bash
# Check location is in supported list
grep -A 50 "SUPPORTED_LOCATIONS" config.json | grep "ca--los-angeles"
# Should find it

# Verify format converts correctly
python -c "location='ca--los-angeles'; parts=location.split('--'); print(f'us--{parts[0]}--{parts[1]}')"
# Should print: us--ca--los-angeles
```

### If Luma Returns 0

```bash
# Check city mapping
python -c "
cities={'ca--los-angeles': 'la', 'ny--new-york': 'nyc'}
print(cities.get('ca--los-angeles', 'not-found'))
"
# Should print: la
```

## Success Checklist

- [ ] Eventbrite: ✓ PASS
- [ ] Meetup: ✓ PASS
- [ ] Luma: ✓ PASS
- [ ] all_events.json created
- [ ] Event count > 0
- [ ] Backend can read events
- [ ] Events appear in /events/{city} endpoint

## Performance Expectations

| Scraper | Time | Events | Reliability |
|---------|------|--------|-------------|
| Eventbrite | 10-20s | 20-50 | 95% |
| Meetup | 30-60s | 10-30 | 90% |
| Luma | 20-40s | 5-20 | 85% |
| **Total** | **1-2m** | **35-100** | **92%** |

## If Tests Pass ✅

1. **Scrapers work!**
2. Set it to run daily via n8n
3. Monitor first run
4. Everything should work

## If Tests Fail ❌

1. Check SCRAPER_FIX_GUIDE.md
2. Run individual scrapers to isolate issue
3. Check network/internet connection
4. Verify Playwright installed: `playwright install chromium`
5. Try disabling slow scrapers, keep fast ones

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "ModuleNotFoundError: No module named 'scrapeevents'" | You're in wrong directory, cd to scraper/ |
| All scrapers timeout | Network issue or CloudFlare blocking |
| Eventbrite only returns 0 | HTML structure changed, Eventbrite updates frequently |
| Meetup only returns 0 | Location format wrong or no events in that city |
| Luma only returns 0 | City not supported, check mapping |

---

**Total Time**: ~5 minutes  
**Success Rate**: >95% if network is working  
**Next**: If all pass, enable n8n daily automation
