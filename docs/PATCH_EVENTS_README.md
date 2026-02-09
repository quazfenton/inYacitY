# Event Data Patching & Maintenance Tool

A comprehensive script for cleaning, validating, and repairing event data in your local JSON files.

## Features

- **Check Missing Fields**: Identify events with incomplete data
- **Sanitize Data**: Clean text fields (remove zero-width chars, normalize whitespace)
- **Backfill Fields**: Populate empty fields from other fields or default values
- **Revisit Links**: Identify events needing re-scraping for missing data
- **Validate Data**: Comprehensive validation against data quality rules
- **Deduplicate**: Remove duplicate events based on content hash
- **Dry Run Mode**: Preview changes without modifying files

## Quick Start

```bash
# Check for missing data
python patch_events.py --check-missing

# Sanitize all text fields
python patch_events.py --sanitize

# Preview changes (dry run)
python patch_events.py --dry-run --sanitize
```

## Common Use Cases

### 1. Add a New Column/Field to Existing Events

```bash
# Add price_tier field with default value of 0
python patch_events.py --backfill-field price_tier --default-value 0

# Copy description from title for empty descriptions
python patch_events.py --backfill-field description --source-field title

# Add computed field (requires editing script for custom logic)
```

### 2. Clean and Sanitize Data

```bash
# Remove invisible characters, normalize whitespace, validate URLs
python patch_events.py --sanitize

# Check what needs cleaning first
python patch_events.py --dry-run --sanitize
```

### 3. Find Events Needing Re-scraping

```bash
# Find events with empty descriptions but valid links
python patch_events.py --revisit-links --field description

# Set minimum content length
python patch_events.py --revisit-links --field description --min-length 50
```

### 4. Validate Data Quality

```bash
# Check all events for errors
python patch_events.py --validate-all

# Generate detailed report
python patch_events.py --validate-all --report validation_report.json
```

### 5. Remove Duplicates

```bash
# Find and remove duplicate events
python patch_events.py --deduplicate

# Preview duplicates without removing
python patch_events.py --dry-run --deduplicate
```

### 6. Complex Operations

```bash
# Run multiple operations and generate report
python patch_events.py \
  --check-missing \
  --sanitize \
  --backfill-field description --source-field title \
  --deduplicate \
  --report maintenance_report.json
```

## Command Reference

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--events-file` | Path to events JSON file | `all_events.json` |
| `--dry-run` | Preview changes without saving | `False` |
| `--report` | Generate JSON report file | None |
| `--verbose` | Show detailed output | `False` |

### Operations

#### `--check-missing`
Identifies events missing required fields (title, date, location, link, source).

```bash
python patch_events.py --check-missing
```

Output shows:
- Total events checked
- Events with missing fields
- First 5 problematic events with details

#### `--sanitize`
Cleans all text fields in events:
- Removes zero-width characters (invisible chars)
- Normalizes whitespace (multiple spaces → single space)
- Removes control characters
- Truncates to max length (1000 chars for description)
- Validates and fixes URLs

```bash
python patch_events.py --sanitize
```

#### `--backfill-field TARGET`
Populates empty fields in existing events.

**Options:**
- `--source-field FIELD`: Copy value from another field
- `--default-value VALUE`: Use a default value

```bash
# Set default value
python patch_events.py --backfill-field category --default-value "Other"

# Copy from another field
python patch_events.py --backfill-field description --source-field title

# Complex: Use script modification for computed values
```

#### `--revisit-links`
Identifies events that need re-scraping because they have:
- Valid links
- Empty or minimal target field content

```bash
python patch_events.py --revisit-links --field description
```

This generates a list of events to re-scrape (manual or automated).

#### `--validate-all`
Comprehensive validation checking:
- Required fields present
- Date format (YYYY-MM-DD)
- URL validity
- Title length (min 3 chars)
- Description quality
- Data consistency

```bash
python patch_events.py --validate-all
```

#### `--deduplicate`
Removes duplicate events based on content hash (title + date + location + city).

```bash
python patch_events.py --deduplicate
```

## Advanced Usage

### Custom Backfill Logic

To add computed fields, edit the script's `backfill_field` method:

```python
# Example: Compute price tier from price
if target_field == 'price_tier':
    price = event.get('price', 0)
    if price == 0:
        new_value = 0  # Free
    elif price < 2000:
        new_value = 1  # Under $20
    elif price < 5000:
        new_value = 2  # Under $50
    else:
        new_value = 3  # $50+
```

### Batch Processing with Scripts

Create a maintenance script:

```bash
#!/bin/bash
# maintenance.sh

echo "Running data maintenance..."

# 1. Check for issues
python patch_events.py --check-missing --report missing.json

# 2. Clean data
python patch_events.py --sanitize

# 3. Fill empty descriptions
python patch_events.py --backfill-field description --source-field title

# 4. Remove duplicates
python patch_events.py --deduplicate

# 5. Validate
python patch_events.py --validate-all --report validation.json

echo "Maintenance complete!"
```

### Integration with Database Sync

After patching local data, sync to database:

```bash
# 1. Patch local data
python patch_events.py --sanitize --backfill-field description --source-field title

# 2. Sync to database
python -c "from db_sync import DatabaseSyncManager; import asyncio; \
           m = DatabaseSyncManager(); asyncio.run(m.sync_events())"
```

## Output Examples

### Check Missing Fields
```
[CHECK MISSING FIELDS]
Total events checked: 150
Events with missing fields: 12

First 5 problematic events:
  - Concert Night: missing description, source
  - Art Workshop: missing link
  - Food Festival: missing location
```

### Sanitize
```
[SANITIZE EVENTS]
Events sanitized: 45
[OK] Saved data to all_events.json
```

### Backfill Field
```
[BACKFILL FIELD: description]
Events patched: 23
[OK] Saved data to all_events.json
```

### Validation
```
[VALIDATE ALL EVENTS]
Valid events: 148/150
Events with errors: 2
Warnings: 5

First 5 errors:
  - Event XYZ: Missing location, Invalid date format: 2026-13-45
  - Party Time: Title too short
```

## Safety Features

1. **Dry Run Mode**: Use `--dry-run` to preview all changes without modifying files
2. **Backups**: Always backup your data before running patches
3. **Incremental**: Operations only modify events that need changes
4. **Reports**: Use `--report` to generate detailed JSON logs

## Troubleshooting

### "Events file not found"
Ensure you're running from the correct directory or specify `--events-file`:
```bash
python scraper/patch_events.py --events-file scraper/all_events.json
```

### "No changes made"
Use `--verbose` to see detailed output:
```bash
python patch_events.py --sanitize --verbose
```

### Unicode errors
The script handles UTF-8 encoding. If you see encoding errors, check your file encoding:
```bash
file -i all_events.json  # Should show utf-8
```

### Script runs but no events processed
Make sure your JSON structure is correct. The script expects either:
```json
{"events": [...]}
```
or
```json
{"cities": {"city-id": {"events": [...]}}}
```

## Best Practices

1. **Always use `--dry-run` first** on production data
2. **Backup before major operations**:
   ```bash
   cp all_events.json all_events.json.backup.$(date +%Y%m%d)
   ```
3. **Run in sequence**: Check → Sanitize → Backfill → Validate
4. **Monitor reports**: Review generated JSON reports for issues
5. **Regular maintenance**: Schedule weekly/monthly runs

## Integration with CI/CD

Add to your deployment pipeline:

```yaml
# .github/workflows/data-quality.yml
name: Data Quality Check

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2am

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Check data quality
        run: |
          python scraper/patch_events.py --validate-all --report quality.json
          
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: quality-report
          path: quality.json
```

## Contributing

To add new patching operations:

1. Add a new method to `EventDataPatcher` class
2. Add command-line argument in `main()`
3. Document in this README
4. Add example to `--help` text

## License

Part of the Nocturne Event Scraper system.
