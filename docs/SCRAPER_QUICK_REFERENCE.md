# Scraper Quick Reference

## New Scrapers Added

| Scraper | Module | Cities | Features |
|---------|--------|--------|----------|
| **Dice.fm** | `scraper/dice_fm.py` | 12 | Price filtering via URL |
| **RA.co** | `scraper/ra_co.py` | 19 | Detail page scraping |

## Quick Start

### Run All Scrapers (Eventbrite + Meetup + Luma + Dice.fm + RA.co)
```bash
cd scraper
python run.py
```

### Run Individual Scraper
```python
# Dice.fm - Free events
import asyncio
from dice_fm import scrape_dice_fm
asyncio.run(scrape_dice_fm("ca--los-angeles", max_price=0))

# RA.co - With detailed info
from ra_co import scrape_ra_co
asyncio.run(scrape_ra_co("ny--new-york", fetch_details=True))
```

## Configuration

Edit `scraper/config.json`:

### Enable/Disable Scrapers
```json
{
  "MODES": {
    "ENABLE_DICE_FM_SCRAPING": true,
    "ENABLE_RA_CO_SCRAPING": true
  }
}
```

### Set Price Filtering (Dice.fm)
```json
{
  "SOURCES": {
    "DICE_FM": {
      "max_price": 0
    }
  }
}
```

**Price values:**
- `0` = Free events only (default)
- `2000` = Events under $20
- `5000` = Events under $50
- `1000000` = All events (no filter)

### Configure Detail Fetching (RA.co)
```json
{
  "SOURCES": {
    "RA_CO": {
      "fetch_detail_pages": true
    }
  }
}
```

## City Codes

### Dice.fm (12 cities)
- `dc--washington`
- `fl--miami`
- `ga--atlanta`
- `il--chicago`
- `on--toronto`
- `ny--new-york`
- `pa--philadelphia`
- `tx--austin`
- `ca--san-francisco`
- `ca--los-angeles`
- `ca--san-diego`
- `wa--seattle`

### RA.co (19 cities)
All 12 above + 7 additional:
- `co--denver`
- `ma--boston`
- `tx--houston`
- `az--phoenix`
- `tx--dallas`
- `nv--las-vegas`
- `ut--salt-lake-city`

## Output Files

| Scraper | Output File |
|---------|------------|
| Dice.fm | `scraper/dice_events.json` |
| RA.co | `scraper/ra_co_events.json` |
| All sources | `scraper/all_events.json` |

## Data Structure

```json
{
  "title": "Event Name",
  "date": "2026-02-07",
  "time": "10:00 PM",
  "location": "Venue Name",
  "link": "https://...",
  "description": "Event description (optional)",
  "source": "Dice.fm" | "RA.co",
  "price": "$20" | "Free" (optional)
}
```

## Price Filtering Details

### Dice.fm
- **Method**: URL query parameter `?priceTo=`
- **Example**: `https://dice.fm/browse/losangeles?priceTo=1` (free)
- **Configurable**: Yes, via `max_price` config
- **Default**: Free events only

### RA.co
- **Method**: No URL-based filtering
- **Note**: All events scraped, filtering must be client-side
- **Future**: Can implement post-processing filter

## Common Issues & Solutions

### No events found
1. Check city code is in supported list
2. Verify internet connection
3. Try with a different city
4. Check if website structure has changed

### Duplicate events
- Clear the output JSON file to rescrape
- Links are tracked to prevent duplicates

### Browser issues
- Ensure `consent_handler.py` exists
- Try setting `use_pydoll=False` in scraper code

## Configuration Presets

### Default (Free events only)
```json
{
  "MODES": {
    "ENABLE_DICE_FM_SCRAPING": true,
    "ENABLE_RA_CO_SCRAPING": true
  },
  "SOURCES": {
    "DICE_FM": {
      "max_price": 0
    },
    "RA_CO": {
      "fetch_detail_pages": true
    }
  }
}
```

### All Events (Including Paid)
```json
{
  "SOURCES": {
    "DICE_FM": {
      "max_price": 1000000
    }
  }
}
```

### Events Under $20
```json
{
  "SOURCES": {
    "DICE_FM": {
      "max_price": 2000
    }
  }
}
```

## Performance Notes

- **Dice.fm**: Fast (listing page only)
- **RA.co with details**: Slower (1-2s per event)
- **RA.co without details**: Fast (listing page only)
- Toggle `fetch_detail_pages: false` for speed

## Monitoring

Check run output for:
```
[4/5] Scraping Dice.fm for ca--los-angeles...
✓ Dice.fm total: 15 events

[5/5] Scraping RA.co for ca--los-angeles...
✓ RA.co total: 23 events
```

Final summary shows:
```
Summary:
  Dice.fm events: 15
  RA.co events: 23
  Total unique: 38
```

## Next Steps

1. Test with `python run.py` in scraper directory
2. Adjust city code in `config.json` as needed
3. Customize price filtering for Dice.fm
4. Review output in `all_events.json`
5. Set up cron/scheduler for regular updates

## File References

- **Scrapers**: `scraper/dice_fm.py`, `scraper/ra_co.py`
- **Configuration**: `scraper/config.json`
- **Orchestration**: `scraper/run.py`
- **Documentation**: `scraper/NEW_SCRAPERS.md`
- **Summary**: `SCRAPER_ADDITIONS_SUMMARY.md`
