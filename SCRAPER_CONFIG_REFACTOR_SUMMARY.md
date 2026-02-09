# Scraper Configuration Refactor Summary

## What Was Done

Refactored all scraper modules to use a **centralized configuration system** instead of hardcoded values. This provides modularity, maintainability, and easy configuration changes.

## Files Modified

### Core Files Updated

1. **eventbrite_scraper.py** - Updated to load config from `config_loader`
   - Now reads `LOCATION` and `EVENTBRITE.main_pages` from config
   - Fallback to defaults if config missing

2. **dice_scraper.py** - Updated to load config
   - Now reads `max_price` and `city_map` from config
   - Supports dynamic price filtering

3. **luma_scraper.py** - Updated to load config
   - Now uses `LUMA.location_map` from config
   - Automatically converts city codes to Luma format

4. **meetup_scraper.py** - Updated to load config
   - Now uses `LOCATION` and converts to Meetup format automatically
   - Configuration-driven location handling

5. **posh_vip.py** - Updated to load config
   - Now uses `POSH_VIP.city_map` from config
   - City mapping is now centralized

### New Files Created

1. **config_loader.py** - Central configuration management
   - Singleton pattern for global config access
   - Dot-notation getter (`get('BROWSER.HEADLESS')`)
   - Helper methods for common patterns
   - Automatic fallback to defaults

2. **config.json** - Centralized configuration file
   - All scraper settings in one place
   - City mappings for each source
   - Browser settings
   - Price filtering modes
   - Deduplication settings
   - Output options

3. **run.py** - Updated orchestrator
   - Uses `config_loader` for all settings
   - Checks `config.is_scraper_enabled()` before running
   - Reads scraper-specific configs
   - No hardcoded location conversions

### Documentation Created

1. **CONFIG_USAGE.md** - How to use the configuration system
   - Configuration structure explained
   - Usage examples
   - How to access config in scrapers

2. **CITY_CODES.md** - City code reference
   - All 44+ supported cities listed
   - City code format explained
   - Scraper support matrix

## Architecture

```
┌─────────────────────────────────────┐
│      config.json                    │
│  (centralized configuration)        │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│      config_loader.py               │
│  (Config singleton + accessors)     │
└────────────┬────────────────────────┘
             │
      ┌──────┴──────┬──────────┬──────────┬─────────┐
      ↓             ↓          ↓          ↓         ↓
   eventbrite   meetup      luma       dice    posh_vip
   _scraper.py _scraper.py _scraper.py _scraper.py .py
      │             │          │          │         │
      └─────────────┴──────────┴──────────┴─────────┘
             │
             ↓
        run.py
   (orchestrator)
```

## Configuration Structure

### Key Sections

**LOCATION** - Default city to scrape
```json
"LOCATION": "ca--los-angeles"
```

**BROWSER** - Browser settings
```json
"BROWSER": {
  "HEADLESS": true,
  "TIMEOUT": 30000,
  "WAIT_TIME": 2000
}
```

**SCRAPER_SETTINGS** - Per-scraper config
```json
"SCRAPER_SETTINGS": {
  "EVENTBRITE": { ... },
  "MEETUP": { ... },
  "LUMA": { ... },
  "DICE_FM": { ... },
  "RA_CO": { ... },
  "POSH_VIP": { ... }
}
```

## Usage Examples

### Quick Configuration Changes

**Change location** (edit config.json):
```json
"LOCATION": "ny--new-york"
```

**Disable slow scrapers**:
```json
"SCRAPER_SETTINGS": {
  "RA_CO": { "enabled": false }
}
```

**Set price filter**:
```json
"SCRAPER_SETTINGS": {
  "DICE_FM": { "max_price": 2000 }  // Under $20
}
```

### In Code

```python
from config_loader import get_config

config = get_config()

# Get location
city = config.get_location()

# Get scraper config
dice_config = config.get_scraper_config('DICE_FM')
max_price = dice_config.get('max_price', 0)

# Check if enabled
if config.is_scraper_enabled('LUMA'):
    # Run Luma scraper
```

## Migration Benefits

✓ **Modularity** - Configuration separate from code
✓ **Easy Testing** - Change config without editing code
✓ **No Hardcoding** - All city mappings in config
✓ **Maintainability** - Single source of truth for settings
✓ **Flexibility** - Easy to add new settings
✓ **Multi-Environment** - Different configs for dev/staging/prod

## Backward Compatibility

All scrapers maintain backward compatibility:
- If `config.json` missing, defaults are used
- Existing function signatures unchanged
- Optional parameters use config if not provided
- No breaking changes to API

## Testing the Configuration

```bash
# Test config loads correctly
python3 -c "from config_loader import get_config; \
config = get_config(); \
print('Location:', config.get_location()); \
print('Dice.fm price:', config.get_scraper_config('DICE_FM').get('max_price'))"

# Run all scrapers with current config
python run.py

# Run specific scraper with custom location
python -c "import asyncio; \
from eventbrite_scraper import scrape_eventbrite; \
asyncio.run(scrape_eventbrite('ny--new-york'))"
```

## Next Steps

1. **Test all scrapers** with new config system
2. **Adjust city mappings** as needed per source
3. **Fine-tune price filters** for each source
4. **Monitor performance** and adjust browser settings
5. **Extend config** with new settings as needed

## Files Changed Summary

| File | Type | Change |
|------|------|--------|
| config.json | Updated | Clean rebuild with all sections |
| config_loader.py | New | Configuration management system |
| eventbrite_scraper.py | Modified | Import config, use in function |
| dice_scraper.py | Modified | Import config, use city_map |
| luma_scraper.py | Modified | Import config, use location_map |
| meetup_scraper.py | Modified | Import config, auto-convert location |
| posh_vip.py | Modified | Import config, use city_map |
| run.py | Rewritten | Use config_loader throughout |
| CONFIG_USAGE.md | New | Configuration reference guide |
| CITY_CODES.md | New | City code reference |

## Configuration is Now Ready

All scrapers are configured and ready to use. Changes can be made by editing `config.json` without touching any Python code.
