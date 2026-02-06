# Scraper Testing & Optimization Checklist

Comprehensive testing workflow for validating and optimizing all scrapers.

## Pre-Testing Setup

### Environment
- [ ] Browser drivers installed (Playwright)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Config file updated (`config.json`)
- [ ] Output directory ready
- [ ] Network connectivity verified

### Configuration
- [ ] Set test city in `config.json`
- [ ] Verify `LOCATION` field
- [ ] Check browser preferences (headless/visible)
- [ ] Set page limits for quick testing
- [ ] Enable logging/debug mode

---

## Individual Scraper Testing

### Test Luma

**Command:** `python luma.py`

**Checklist:**
- [ ] Browser launches successfully
- [ ] Page loads within timeout
- [ ] Date headers detected
- [ ] Event cards found (count logged)
- [ ] Titles extracted correctly
- [ ] Dates parsed (no invalid formats)
- [ ] Times extracted (or TBA)
- [ ] Locations detected
- [ ] Links generated correctly
- [ ] Descriptions fetched from detail pages
- [ ] Output file created (`luma_events.json`)
- [ ] No duplicate events in output
- [ ] File is valid JSON

**Sample Output Check:**
```json
{
  "events": [
    {
      "title": "Event Name",
      "date": "2026-02-XX",
      "time": "XX:XX",
      "location": "Venue Name",
      "link": "https://luma.com/eventid",
      "description": "Event description",
      "source": "Luma"
    }
  ]
}
```

**Quality Gates:**
- [ ] ≥ 80% of fields complete
- [ ] No "TBA" for date
- [ ] No malformed URLs
- [ ] Description length > 20 chars

---

### Test Meetup

**Command:** `python -c "import asyncio; from meetup import scrape_meetup_events; asyncio.run(scrape_meetup_events('us--ca--los-angeles', []))"`

**Checklist:**
- [ ] Meetup API accessible
- [ ] Events returned for location
- [ ] Group names extracted
- [ ] Event dates in correct format
- [ ] URLs properly formatted
- [ ] Description fetched if available
- [ ] Attendance numbers accurate
- [ ] No API rate limiting
- [ ] Output has no duplicates
- [ ] Source marked as "Meetup"

**Expected Data:**
- Title: group name + event name
- Date: YYYY-MM-DD format
- Time: HH:MM or TBA
- Location: extracted from group/event
- Link: https://meetup.com/events/...

---

### Test Eventbrite

**Command:** `python scrapeevents.py` (or individual Eventbrite function)

**Checklist:**
- [ ] Page loads (may need CAPTCHA handling)
- [ ] Event cards identified
- [ ] Titles extracted (≥95%)
- [ ] Dates parsed correctly
- [ ] Prices detected (free vs paid)
- [ ] Location extracted
- [ ] Event links work
- [ ] Description field populated
- [ ] Image URL captured
- [ ] No rate limiting/blocking
- [ ] File saved as `all_events.json`

**Data Validation:**
- [ ] Title: not empty, >3 characters
- [ ] Date: valid YYYY-MM-DD format
- [ ] Price: 0 for free, cents for paid
- [ ] Location: venue name + city
- [ ] Link: eventbrite.com domain

---

### Test Dice.fm

**Command:** `python dice_fm.py`

**Checklist:**
- [ ] Browser loads dice.fm
- [ ] City URL correct
- [ ] Price filter applied (?priceTo=1 for free)
- [ ] Event cards detected
- [ ] Titles from images/divs
- [ ] Dates extracted
- [ ] Venue names found
- [ ] Links generated
- [ ] Price defaults to 0 (free)
- [ ] No blocking/rate limiting
- [ ] Output file created

**Selector Effectiveness:**
- [ ] Event title: ≥90% success
- [ ] Venue: ≥80% success
- [ ] Date: ≥85% success
- [ ] Link: 100% success (required)

**Quality Checks:**
- [ ] `source: "Dice.fm"` tag
- [ ] No duplicate links
- [ ] Dates are upcoming
- [ ] All from correct city

---

### Test RA.co

**Command:** `python ra_co.py`

**Checklist:**
- [ ] RA.co events page loads
- [ ] City URL constructed correctly
- [ ] Title links detected
- [ ] Listing page titles extracted
- [ ] Detail pages fetched (if enabled)
- [ ] Dates parsed from detail page
- [ ] Times extracted
- [ ] Location detected
- [ ] Description populated
- [ ] Price extracted
- [ ] JSON-LD data parsed (if present)
- [ ] Coordinates captured
- [ ] No blocking detected
- [ ] Output file created (`ra_co_events.json`)

**Detail Page Checks (if enabled):**
- [ ] Load time acceptable (<2s per event)
- [ ] Data more complete than listing
- [ ] No extra data loss
- [ ] Description quality improved

---

### Test Posh.vip

**Command:** `python posh_vip.py`

**Checklist:**
- [ ] Posh.vip page loads
- [ ] City-specific URL works
- [ ] Event cards found
- [ ] Titles extracted
- [ ] Venue information captured
- [ ] Date/time detected
- [ ] Price tiers identified (if multiple)
- [ ] Open bar detection working
- [ ] Links generated correctly
- [ ] Category tagged as "club"
- [ ] Output saved
- [ ] Manual trigger only (not auto-scheduled)

**Specific to Posh.vip:**
- [ ] Open bar detection accuracy
- [ ] Price tier separation (VIP vs General)
- [ ] Dress code captured (if available)
- [ ] Age restriction noted

---

## Data Quality Testing

### Completeness Analysis

```python
# Run: python test_scrapers.py
```

**Check Results:**
- [ ] Title: ≥95% complete
- [ ] Date: ≥85% complete
- [ ] Location: ≥85% complete
- [ ] Time: ≥70% complete
- [ ] Link: 100% complete
- [ ] Description: ≥50% complete

### Data Format Validation

**Dates:**
- [ ] Format: YYYY-MM-DD
- [ ] All in future (after today)
- [ ] No invalid dates (Feb 30, etc.)
- [ ] No hardcoded dates

**Times:**
- [ ] Format: HH:MM or "TBA"
- [ ] Valid hours (0-23)
- [ ] Valid minutes (0-59)
- [ ] TBA acceptable fallback

**Locations:**
- [ ] Contains venue/street
- [ ] Contains city (if available)
- [ ] Length < 255 chars
- [ ] No "TBA" acceptable only if rare

**Links:**
- [ ] Valid HTTP/HTTPS URLs
- [ ] Domain matches source
- [ ] Unique (no duplicates in same scraper)
- [ ] Clickable/working (spot check)

---

## Deduplication Testing

### Duplicate Detection

```python
from scraper_deduplication_strategy import DeduplicationPipeline

pipeline = DeduplicationPipeline()
results = pipeline.run_deduplication(all_events)
```

**Check:**
- [ ] URL deduplication working
- [ ] Content deduplication running
- [ ] Hash verification passing
- [ ] No false positives
- [ ] No false negatives

### Cross-Source Duplicates

**Manually verify:**
- [ ] Same event on multiple platforms
- [ ] Detected by system
- [ ] Correct duplicate flagged
- [ ] Original kept (or best quality)

**Example:** Eventbrite concert also on Luma
- [ ] Both found by respective scrapers
- [ ] Deduplication identifies match
- [ ] One kept, one removed
- [ ] Quality metrics updated

---

## Performance Testing

### Speed Benchmarks

**Target times per scraper:**
- Luma: < 5 minutes
- Meetup: < 3 minutes
- Eventbrite: < 10 minutes
- Dice.fm: < 2 minutes
- RA.co: < 5 minutes (with details)
- Posh.vip: < 2 minutes

**Measure:**
```python
import time
start = time.time()
# Run scraper
elapsed = time.time() - start
print(f"Elapsed: {elapsed:.2f}s")
```

- [ ] Meet or exceed time targets
- [ ] No timeout errors
- [ ] No hanging processes
- [ ] Network requests fast

### Resource Usage

- [ ] Memory stable (<500MB)
- [ ] CPU reasonable (<50%)
- [ ] Disk I/O acceptable
- [ ] No file handles leaking
- [ ] Browser process closes cleanly

---

## Error Handling Testing

### Test Error Scenarios

**Network Issues:**
- [ ] Timeout handling
- [ ] Retry logic working
- [ ] Error logged
- [ ] Graceful degradation

**Selector Changes:**
- [ ] Fallback selectors tested
- [ ] Error message clear
- [ ] Suggests fix/update needed

**Invalid Data:**
- [ ] Malformed HTML handled
- [ ] Missing fields fallback to "TBA"
- [ ] No crash on edge cases

**Rate Limiting:**
- [ ] 429 status detected
- [ ] Wait/retry implemented
- [ ] User-agent rotation (if needed)

---

## Selector Optimization

### Test Each Selector

**Luma Selectors:**
```python
# Test date title selector
selectors_to_test = [
    'div.date-title',
    'div[class*="date-title"]',
    'div:has(> div.date)'
]
for sel in selectors_to_test:
    success = test_selector(soup, sel)
    print(f"{sel}: {'✓' if success else '✗'}")
```

- [ ] Primary selector works
- [ ] Fallback selector tested
- [ ] Performance acceptable
- [ ] No false positives

**Meetup Selectors:**
- [ ] Group name extracted
- [ ] Event title captured
- [ ] Date/time parsed
- [ ] Link URL valid

**Eventbrite Selectors:**
- [ ] data-testid attributes work
- [ ] Fallback to class names
- [ ] Price parsing robust
- [ ] Location extraction reliable

**Dice.fm Selectors:**
- [ ] Image alt text fallback
- [ ] Class partial matching
- [ ] Link extraction 100%
- [ ] Price parsing handles multiple formats

**RA.co Selectors:**
- [ ] data-pw-test-id working
- [ ] Detail bar content correct
- [ ] JSON-LD fallback
- [ ] Description placement variations

**Posh.vip Selectors:**
- [ ] Event cards found
- [ ] Title/link extraction
- [ ] Price tier parsing
- [ ] Open bar detection accuracy

---

## Integration Testing

### Combined Test

**Command:** `python run.py`

**Checklist:**
- [ ] All scrapers execute sequentially
- [ ] Each produces output file
- [ ] Merge into all_events.json
- [ ] No errors during merge
- [ ] Final count reasonable
- [ ] Duplicates removed
- [ ] File valid JSON

### File Output Validation

- [ ] `luma_events.json` exists
- [ ] `meetup_events.json` exists
- [ ] `dice_events.json` exists
- [ ] `ra_co_events.json` exists
- [ ] `posh_vip_events.json` exists
- [ ] `all_events.json` merged correctly
- [ ] File sizes reasonable
- [ ] No corrupted JSON

---

## Regression Testing

### Before/After Comparison

After making selector changes:

```python
# Run scraper twice and compare
before = load_events('luma_events_before.json')
after = load_events('luma_events_after.json')

# Calculate changes
added = len([e for e in after if e not in before])
removed = len([e for e in before if e not in after])
changed = len([e for e in after if e in before and e != before[before.index(e)]])

print(f"Added: {added}, Removed: {removed}, Changed: {changed}")
```

- [ ] Event count stable (±10%)
- [ ] Data quality improved or stable
- [ ] No major data loss
- [ ] New selectors more effective

---

## Documentation Testing

### Verify Guides

- [ ] Selector guide matches actual selectors
- [ ] Deduplication docs match code
- [ ] Examples run without error
- [ ] Configuration options documented
- [ ] Troubleshooting covers common issues

---

## Sign-Off Checklist

**Before marking scrapers as production-ready:**

- [ ] All 6 scrapers tested
- [ ] Data quality metrics met
- [ ] No major errors
- [ ] Deduplication working
- [ ] Performance acceptable
- [ ] Integration successful
- [ ] Documentation complete
- [ ] Examples verified
- [ ] Regression test passed
- [ ] Team review completed

---

## Troubleshooting Guide

### Scraper Produces No Events

1. [ ] Check URL in browser (manual test)
2. [ ] Verify selectors in inspect element
3. [ ] Check console for JavaScript errors
4. [ ] Wait longer for dynamic content
5. [ ] Check for anti-bot detection
6. [ ] Review browser logs
7. [ ] Try different browser/headless setting

### Data Incomplete (Missing Fields)

1. [ ] Check if field exists in HTML
2. [ ] Test selector in Python console
3. [ ] Review fallback selector list
4. [ ] Consider field optional (mark TBA)
5. [ ] Check if data is in detail page
6. [ ] Verify extraction logic

### Duplicates Not Detected

1. [ ] Check if URLs identical
2. [ ] Manually compare events
3. [ ] Verify deduplication running
4. [ ] Check similarity threshold
5. [ ] Test with debug output
6. [ ] Review hash generation

### Performance Issues

1. [ ] Profile with time.time()
2. [ ] Check network speed
3. [ ] Review page load waits
4. [ ] Optimize selectors (fewer specificity)
5. [ ] Reduce page scrolling/interactions
6. [ ] Consider caching/storage

---

## Continuous Monitoring

### Weekly Checks

- [ ] Run full scraper suite
- [ ] Check for selector breaks
- [ ] Monitor duplicate rate
- [ ] Verify data quality metrics
- [ ] Check for error patterns

### Monthly Review

- [ ] Analyze duplicate patterns
- [ ] Assess selector effectiveness
- [ ] Plan selector updates
- [ ] Review performance trends
- [ ] Update documentation

---

**Version:** 1.0  
**Last Updated:** 2026-02-05  
**Frequency:** After each scraper change, before production deployment
