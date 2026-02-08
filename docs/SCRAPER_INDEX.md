# Event Scraper Modules Index

## Quick Navigation

### Get Started Fast
- **Start here**: [`SCRAPER_QUICK_REFERENCE.md`](./SCRAPER_QUICK_REFERENCE.md) - 5-minute quick start
- **Configure**: Edit `scraper/config.json` for price filtering and city selection
- **Run**: `cd scraper && python run.py`

### Detailed Information
- **Full Guide**: [`scraper/NEW_SCRAPERS.md`](./scraper/NEW_SCRAPERS.md) - Comprehensive documentation
- **Implementation**: [`IMPLEMENTATION_CHECKLIST.md`](./IMPLEMENTATION_CHECKLIST.md) - What's been done
- **Summary**: [`SCRAPER_ADDITIONS_SUMMARY.md`](./SCRAPER_ADDITIONS_SUMMARY.md) - Complete overview

## Scraper Modules

### 1. Dice.fm Scraper
**File**: `scraper/dice_fm.py`  
**Purpose**: Scrape electronic music events from Dice.fm  
**Cities**: 12 (DC, Miami, Atlanta, Chicago, Toronto, NYC, Philadelphia, Austin, SF, LA, San Diego, Seattle)  
**Features**:
- URL-based price filtering
- Event listing page scraping
- Optional detail page scraping
- Duplicate detection

**Usage**:
```python
from dice_fm import scrape_dice_fm
await scrape_dice_fm("ca--los-angeles", max_price=0)  # Free events
await scrape_dice_fm("ny--new-york", max_price=2000)  # Under $20
```

**Configuration** (in `config.json`):
```json
{
  "MODES": {
    "ENABLE_DICE_FM_SCRAPING": true
  },
  "SOURCES": {
    "DICE_FM": {
      "enabled": true,
      "max_price": 0
    }
  }
}
```

### 2. RA.co Scraper
**File**: `scraper/ra_co.py`  
**Purpose**: Scrape electronic music events from RA.co  
**Cities**: 19 (All Dice.fm cities + Denver, Boston, Houston, Phoenix, Dallas, Las Vegas, Salt Lake City)  
**Features**:
- Listing page scraping
- Optional detail page scraping for each event
- JSON-LD structured data extraction
- Geographic coordinate parsing

**Usage**:
```python
from ra_co import scrape_ra_co
await scrape_ra_co("ca--san-francisco", fetch_details=True)
await scrape_ra_co("il--chicago", fetch_details=False)  # Faster
```

**Configuration** (in `config.json`):
```json
{
  "MODES": {
    "ENABLE_RA_CO_SCRAPING": true
  },
  "SOURCES": {
    "RA_CO": {
      "enabled": true,
      "fetch_detail_pages": true
    }
  }
}
```

## Master Orchestrator

**File**: `scraper/run.py`  
**Purpose**: Run all scrapers and merge results

**Execution Steps**:
1. Eventbrite scraping [1/6]
2. Meetup scraping [2/6]
3. Luma scraping [3/6]
4. Dice.fm scraping [4/6] ← NEW
5. RA.co scraping [5/6] ← NEW
6. Merge and save [6/6]

**Run All Scrapers**:
```bash
cd scraper
python run.py
```

**Output**: `scraper/all_events.json` (merged events from all sources)

## Configuration Guide

**File**: `scraper/config.json`

### Global Settings
```json
{
  "LOCATION": "ca--los-angeles",
  "SUPPORTED_LOCATIONS": [
    "ca--los-angeles",
    "ny--new-york",
    ...
  ]
}
```

### Scraper Controls
```json
{
  "MODES": {
    "ENABLE_DICE_FM_SCRAPING": true,
    "ENABLE_RA_CO_SCRAPING": true,
    "ENABLE_MEETUP_SCRAPING": true,
    "ENABLE_LUMA_SCRAPING": true,
    "ENABLE_EVENTBRITE_SCRAPING": true
  }
}
```

### Price Filtering Modes
```json
{
  "SOURCES": {
    "PRICE_FILTER_MODE": {
      "FREE_ONLY": 0,
      "UNDER_20_DOLLARS": 2000,
      "UNDER_50_DOLLARS": 5000,
      "NO_FILTER": 1000000
    }
  }
}
```

### Dice.fm Configuration
```json
{
  "DICE_FM": {
    "enabled": true,
    "max_price": 0,
    "description": "0=free only, other=max price in cents, 1000000+=no filter"
  }
}
```

### RA.co Configuration
```json
{
  "RA_CO": {
    "enabled": true,
    "fetch_detail_pages": true,
    "description": "RA.co does not support price filtering via URL"
  }
}
```

## Output Files

| File | Source | Format |
|------|--------|--------|
| `scraper/dice_events.json` | Dice.fm | `{events: [...], count: N, new: N}` |
| `scraper/ra_co_events.json` | RA.co | `{events: [...], count: N, new: N}` |
| `scraper/all_events.json` | All sources | `{events: [...], total: N, location: X, last_updated: T}` |

## Event Data Structure

```json
{
  "title": "Event Name",
  "date": "2026-02-07",
  "time": "10:00 PM",
  "location": "Venue Name",
  "link": "https://...",
  "description": "Event description (optional)",
  "source": "Dice.fm" | "RA.co" | "Luma" | "Meetup" | "Eventbrite",
  "price": "$20" | "Free" (optional)
}
```

## Supported Cities

### Dice.fm (12 cities)
- `ca--los-angeles` - Los Angeles
- `ca--san-diego` - San Diego
- `ca--san-francisco` - San Francisco
- `dc--washington` - Washington DC
- `fl--miami` - Miami
- `ga--atlanta` - Atlanta
- `il--chicago` - Chicago
- `ny--new-york` - New York
- `on--toronto` - Toronto
- `pa--philadelphia` - Philadelphia
- `tx--austin` - Austin
- `wa--seattle` - Seattle

### RA.co (19 cities)
All of above +
- `az--phoenix` - Phoenix
- `co--denver` - Denver
- `ma--boston` - Boston
- `nv--las-vegas` - Las Vegas
- `tx--dallas` - Dallas
- `tx--houston` - Houston
- `ut--salt-lake-city` - Salt Lake City

## Documentation Files

| File | Purpose | Lines |
|------|---------|-------|
| `SCRAPER_QUICK_REFERENCE.md` | Quick start guide | 300+ |
| `scraper/NEW_SCRAPERS.md` | Comprehensive docs | 180 |
| `SCRAPER_ADDITIONS_SUMMARY.md` | Detailed summary | 250+ |
| `IMPLEMENTATION_CHECKLIST.md` | Implementation details | 217 |
| `SCRAPER_INDEX.md` | This file | Navigation |

## Getting Help

### Common Issues

**No events found?**
- Check city code is supported
- Verify internet connection
- Try `LOCATION: "ny--new-york"` in config.json

**Duplicate events?**
- Clear output JSON file and rescrape
- Links are tracked automatically

**Browser issues?**
- Ensure `consent_handler.py` exists
- Check playwright drivers installed

### Configuration Examples

**Free events only** (default):
```json
{
  "SOURCES": {
    "DICE_FM": {
      "max_price": 0
    }
  }
}
```

**All events including paid**:
```json
{
  "SOURCES": {
    "DICE_FM": {
      "max_price": 1000000
    }
  }
}
```

**Fast RA.co (no detail pages)**:
```json
{
  "SOURCES": {
    "RA_CO": {
      "fetch_detail_pages": false
    }
  }
}
```

## File Structure

```
/home/workspace/inyAcity/
├── scraper/
│   ├── config.json               ← Configuration
│   ├── run.py                    ← Master orchestrator
│   ├── dice_fm.py                ← NEW: Dice.fm scraper
│   ├── ra_co.py                  ← NEW: RA.co scraper
│   ├── luma.py                   ← Existing: Luma scraper
│   ├── meetup.py                 ← Existing: Meetup scraper
│   ├── scrapeevents.py           ← Existing: Eventbrite scraper
│   ├── consent_handler.py        ← Browser automation
│   ├── all_events.json           ← Output: Merged events
│   ├── dice_events.json          ← Output: Dice.fm only
│   ├── ra_co_events.json         ← Output: RA.co only
│   └── NEW_SCRAPERS.md           ← NEW: Full documentation
├── SCRAPER_INDEX.md              ← NEW: This file
├── SCRAPER_QUICK_REFERENCE.md    ← NEW: Quick start
├── SCRAPER_ADDITIONS_SUMMARY.md  ← NEW: Summary
└── IMPLEMENTATION_CHECKLIST.md   ← NEW: Checklist
```

## Performance Tips

- **Fast mode**: Set `fetch_detail_pages: false` for RA.co
- **Selective**: Only enable scrapers you need
- **Free only**: Default `max_price: 0` for Dice.fm
- **Parallel**: All scrapers run in sequence; could be parallelized

## Next Steps

1. **Test**: `cd scraper && python run.py`
2. **Review**: Check `all_events.json` output
3. **Configure**: Adjust `config.json` for your needs
4. **Schedule**: Set up cron job for regular updates
5. **Enhance**: Add pagination, filtering, or other features

## Version Info

- **Created**: 2026-02-05
- **Status**: Ready to Deploy
- **Code Files**: 2 scrapers (647 lines)
- **Documentation**: 4 files (900+ lines)
- **Cities**: 31 supported
- **Price Modes**: 4 options

---

For detailed information, see:
- [`scraper/NEW_SCRAPERS.md`](./scraper/NEW_SCRAPERS.md) - Complete guide
- [`SCRAPER_QUICK_REFERENCE.md`](./SCRAPER_QUICK_REFERENCE.md) - Quick reference
- [`IMPLEMENTATION_CHECKLIST.md`](./IMPLEMENTATION_CHECKLIST.md) - What's been done
