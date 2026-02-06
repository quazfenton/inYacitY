# Scraper Additions Summary - Dice.fm & RA.co

## Files Created

### 1. `/scraper/dice_fm.py` (293 lines)
**Dice.fm Event Scraper** - Scrapes electronic music events from Dice.fm with price filtering

**Key Features:**
- City-to-URL mapping for 12 supported cities
- Configurable price filtering (free only, under $X, or all events)
- Event detail scraping from listing pages
- Duplicate detection via link tracking
- JSON output with event metadata

**Main Functions:**
- `build_dice_fm_url()` - Builds URLs with price filters
- `fetch_dice_events_from_page()` - Scrapes listing page events
- `scrape_dice_fm_detail_page()` - Gets details from individual event pages
- `scrape_dice_fm()` - Main entry point

### 2. `/scraper/ra_co.py` (354 lines)
**RA.co Event Scraper** - Scrapes electronic music events from RA.co with detailed extraction

**Key Features:**
- City-to-URL mapping for 19 supported cities
- Optional detailed page scraping for each event
- CSS selector-based data extraction
- JSON-LD structured data parsing
- Geographic coordinate extraction

**Main Functions:**
- `build_ra_co_url()` - Builds city-specific URLs
- `fetch_ra_co_events_from_page()` - Scrapes listing page
- `scrape_ra_co_detail_page()` - Gets detailed info from event pages
- `scrape_ra_co()` - Main entry point

## Configuration Updates

### `/scraper/config.json`
Added comprehensive source configuration with:

```json
"SOURCES": {
  "PRICE_FILTER_MODE": {
    "FREE_ONLY": 0,
    "UNDER_20_DOLLARS": 2000,
    "UNDER_50_DOLLARS": 5000,
    "NO_FILTER": 1000000
  },
  "DICE_FM": {
    "enabled": true,
    "max_price": 0,
    "supported_cities": [12 cities]
  },
  "RA_CO": {
    "enabled": true,
    "fetch_detail_pages": true,
    "supported_cities": [19 cities]
  }
}
```

Also added to `MODES`:
- `ENABLE_DICE_FM_SCRAPING: true`
- `ENABLE_RA_CO_SCRAPING: true`

## Integration Updates

### `/scraper/run.py`
Updated master scraper orchestrator to:
- Import and run both new scrapers
- Extract price configuration for Dice.fm
- Extract detail-page flag for RA.co
- Include results in final merge
- Add source counts to summary output

**Steps added:**
- [4/5] Dice.fm scraping
- [5/5] RA.co scraping
- Updated merge step to [6/6]

## Documentation

### `/scraper/NEW_SCRAPERS.md` (180 lines)
Comprehensive documentation covering:
- Feature overview
- Supported cities for each scraper
- Price filtering configuration
- Generalized price filtering modes
- Integration details
- Data format specifications
- Browser automation details
- Error handling
- Usage examples
- Future enhancement ideas
- Troubleshooting guide
- Full configuration reference

## Supported Cities

### Dice.fm (12 cities)
DC, Miami, Atlanta, Chicago, Toronto, NYC, Philadelphia, Austin, SF, LA, San Diego, Seattle

### RA.co (19 cities)
All Dice.fm cities + Denver, Boston, Houston, Phoenix, Dallas, Las Vegas, Salt Lake City

## Price Filtering Strategy

**Dice.fm:**
- Supports URL-based filtering: `?priceTo=1` (free) through `?priceTo=X` (under $X)
- Default: Free events only (`max_price=0`)
- Configurable per source

**RA.co:**
- No URL-based filtering support
- Future: Can implement client-side filtering after scraping
- Note: Site varies in detail availability

## Generalized Configuration

Introduced `PRICE_FILTER_MODE` constants for future extensibility:
- Different sites have different filtering capabilities
- Constants can be referenced in site-specific configs
- Ready for application to database queries and user filters
- Allows client-side filtering when URL filtering unavailable

## Key Design Decisions

1. **City Mapping** - Hardcoded mappings instead of auto-detection
   - Reason: Each site has non-standardizable URL formats
   - Benefit: Explicit, maintainable, verifiable

2. **Price Filtering** - Generalized mode with site-specific implementation
   - Reason: Not all sites support filtering the same way
   - Benefit: Framework ready for future sites

3. **Detail Scraping** - Optional per-event detail fetching
   - Reason: RA.co has richer detail pages; Dice.fm doesn't
   - Benefit: Configurable verbosity/speed tradeoff

4. **Browser Automation** - Reuses existing `consent_handler`
   - Reason: Consistent anti-detection approach
   - Benefit: CAPTCHA handling, Cloudflare bypass already solved

5. **Duplicate Detection** - Link-based tracking
   - Reason: Same event appears on multiple pages/requests
   - Benefit: Avoids database pollution

## Testing

To test individually:

```bash
# Dice.fm
python -c "import asyncio; from dice_fm import scrape_dice_fm; asyncio.run(scrape_dice_fm('ca--los-angeles'))"

# RA.co
python -c "import asyncio; from ra_co import scrape_ra_co; asyncio.run(scrape_ra_co('ny--new-york'))"

# Both together
python run.py
```

## Future Enhancements

1. Pagination support for multi-page events
2. JavaScript rendering for dynamic content
3. Category/genre filtering
4. Date range filtering
5. API-based scraping when available
6. Client-side price filtering for RA.co
7. Venue/artist search capabilities
8. Event description aggregation
