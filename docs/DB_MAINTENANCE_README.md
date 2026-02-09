# Database Maintenance & Repair Tool

A comprehensive tool for maintaining, repairing, and synchronizing your event database with local data.

## Features

- **Update by Hash/Link**: Fix specific corrupted events in database
- **Sync Patched Events**: Push local fixes to database
- **Remove Recent Events**: Delete events added in last N hours (if corrupted)
- **Remove Orphaned Events**: Delete DB events not in local file
- **Compare Local vs DB**: See differences between local and database
- **Batch Updates**: Fix multiple events at once

## Quick Start

```bash
# Update a specific event by hash
python db_maintenance.py --update-by-hash abc123 --field description --value "Fixed description"

# Sync all patched local events to database
python db_maintenance.py --sync-patched

# Remove events added in last 24 hours
python db_maintenance.py --remove-recent --hours 24

# Preview changes without applying
python db_maintenance.py --sync-patched --dry-run
```

## Use Cases

### 1. Fix Corrupted Event Data

When a scraper run corrupted specific fields:

```bash
# Fix by hash (preferred - unique identifier)
python db_maintenance.py --update-by-hash a1b2c3d4 --field description --value "Corrected description"

# Fix by link (if you know the URL)
python db_maintenance.py --update-by-link "https://eventbrite.com/e/123" --field title --value "Corrected Title"
```

**Available Fields:**
- `title`
- `description`
- `location`
- `date`
- `time`
- `price`
- `price_tier`
- `category`
- `source`

### 2. Revert Bad Scrape (Remove Recent Events)

If the last scrape was corrupted:

```bash
# See what would be removed (dry run)
python db_maintenance.py --remove-recent --hours 2 --dry-run

# Actually remove events from last 2 hours
python db_maintenance.py --remove-recent --hours 2

# Remove events from last 24 hours
python db_maintenance.py --remove-recent --hours 24
```

**Warning:** This permanently deletes events from the database. Use `--dry-run` first!

### 3. Sync Patched Local Events

After running `patch_events.py` to fix local data:

```bash
# First, patch local data
python patch_events.py --sanitize --backfill-field description

# Then sync fixes to database
python db_maintenance.py --sync-patched
```

This updates database events to match your corrected local data.

### 4. Clean Up Orphaned Events

Remove database events that no longer exist locally:

```bash
# Preview what would be removed
python db_maintenance.py --remove-orphaned --dry-run

# Remove orphaned events
python db_maintenance.py --remove-orphaned
```

### 5. Compare Local vs Database

See what's different between local file and database:

```bash
python db_maintenance.py --compare
```

Output shows:
- Events only in local (not synced yet)
- Events only in database (orphaned)
- Events in both (should be identical)

### 6. Batch Update Events

Fix multiple events at once:

```bash
# Change category from "Concert" to "Music" for all matching events
python db_maintenance.py --batch-update --field category --from "Concert" --to "Music"

# Fix source name
python db_maintenance.py --batch-update --field source --from "eventbrite " --to "eventbrite"
```

## Complete Workflow Example

### Scenario: Scraper corrupted descriptions

```bash
# Step 1: Check what was affected
python db_maintenance.py --compare

# Step 2: Remove corrupted events from last scrape (2 hours ago)
python db_maintenance.py --remove-recent --hours 2

# Step 3: Fix local data
python patch_events.py --sanitize --backfill-field description --source-field title

# Step 4: Re-scrape the affected events (if needed)
# ... run scraper for specific city ...

# Step 5: Sync fixed events to database
python db_maintenance.py --sync-patched

# Step 6: Verify
python db_maintenance.py --compare
```

### Scenario: Wrong category detected

```bash
# Update specific event
python db_maintenance.py --update-by-hash abc123 --field category --value "Nightlife"

# Or batch update all wrong categories
python db_maintenance.py --batch-update --field category --from "Club" --to "Nightlife"
```

## Command Reference

### Single Event Updates

#### `--update-by-hash <hash>`
Update a specific event using its unique hash.

**Required with this:**
- `--field <fieldname>`: Which field to update
- `--value <value>`: New value

```bash
python db_maintenance.py \
  --update-by-hash a1b2c3d4e5f6 \
  --field description \
  --value "Updated description text"
```

#### `--update-by-link <url>`
Update event by its link (useful if you don't know the hash).

```bash
python db_maintenance.py \
  --update-by-link "https://eventbrite.com/e/12345" \
  --field title \
  --value "Corrected Event Title"
```

### Bulk Operations

#### `--sync-patched`
Updates all database events to match local file data. Use after patching local events.

```bash
# Preview
python db_maintenance.py --sync-patched --dry-run

# Apply
python db_maintenance.py --sync-patched
```

#### `--remove-recent --hours <n>`
Removes events added within last N hours. Useful for reverting bad scrapes.

```bash
# Remove events from last hour
python db_maintenance.py --remove-recent --hours 1

# Remove events from last 6 hours
python db_maintenance.py --remove-recent --hours 6
```

**Safety:** Always shows list and asks for confirmation (unless `--dry-run`).

#### `--remove-orphaned`
Removes database events that don't exist in local file.

```bash
python db_maintenance.py --remove-orphaned --dry-run
python db_maintenance.py --remove-orphaned
```

### Analysis

#### `--compare`
Shows differences between local file and database.

```bash
python db_maintenance.py --compare
```

Sample output:
```
[COMPARE LOCAL VS DATABASE]
Local events: 150
Database events: 145

Only in local (not synced): 8
Only in database (orphaned): 3
In both: 142

First 5 local-only events:
  - Underground Rave
  - Tech Meetup
  - Art Show
  - Concert Night
  - Food Festival

First 5 database-only events:
  - Old Event 1
  - Old Event 2
  - Old Event 3
```

### Batch Updates

#### `--batch-update --field <field> --from <old> --to <new>`
Update all events matching criteria.

```bash
python db_maintenance.py \
  --batch-update \
  --field category \
  --from "Concert" \
  --to "Live Music"
```

**Safety:** Shows count and asks for confirmation.

## Safety Features

1. **Dry Run Mode** (`--dry-run`)
   - Preview all changes before applying
   - Shows exactly what would be updated/deleted
   - No database modifications

2. **Confirmation Prompts**
   - Destructive operations (delete) require "yes" confirmation
   - Shows list of affected events
   - Can cancel anytime

3. **Selective Updates**
   - Update by hash = exact event
   - Update by link = specific event
   - No accidental mass updates

## Environment Setup

Ensure your environment has:

```bash
# Supabase credentials
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-api-key"

# Or in config.json
{
  "SUPABASE_URL": "https://your-project.supabase.co",
  "SUPABASE_KEY": "your-api-key"
}
```

## Integration with Patch Tool

Combine with `patch_events.py` for complete data repair:

```bash
#!/bin/bash
# repair_data.sh

echo "=== DATA REPAIR WORKFLOW ==="

# 1. Check database vs local
echo "Comparing local vs database..."
python db_maintenance.py --compare

# 2. Patch local data
echo "Patching local data..."
python patch_events.py --sanitize --backfill-field description

# 3. Sync to database
echo "Syncing to database..."
python db_maintenance.py --sync-patched

# 4. Clean up orphans
echo "Removing orphaned events..."
python db_maintenance.py --remove-orphaned

# 5. Verify
echo "Final comparison..."
python db_maintenance.py --compare

echo "=== REPAIR COMPLETE ==="
```

## Troubleshooting

### "No event found with hash"
- Hash might be different in database vs local
- Use `--compare` to find the correct hash
- Or use `--update-by-link` instead

### "Failed to connect to database"
- Check SUPABASE_URL and SUPABASE_KEY environment variables
- Verify Supabase project is active
- Check network connectivity

### "No events in database"
- Database might be empty
- Run `db_sync.py` first to populate database
- Check correct table name ('events')

### Changes not appearing
- Database might have caching
- Wait a few minutes
- Check Supabase dashboard directly

### "Update returned no data"
- Event might not exist
- Hash/link might be incorrect
- Check with `--compare` first

## Best Practices

1. **Always compare first**
   ```bash
   python db_maintenance.py --compare
   ```

2. **Use dry-run for bulk operations**
   ```bash
   python db_maintenance.py --sync-patched --dry-run
   ```

3. **Backup before major changes**
   ```bash
   # Export database backup
   python db_maintenance.py --compare > backup_$(date +%Y%m%d).json
   ```

4. **Update by hash when possible**
   - More precise than link
   - Links can change
   - Hash is consistent

5. **Test on staging first**
   - Use staging database credentials
   - Verify changes look correct
   - Then apply to production

## Common Patterns

### Fix Missing Descriptions
```bash
# Patch local first
python patch_events.py --backfill-field description --source-field title

# Sync to DB
python db_maintenance.py --sync-patched
```

### Remove Test Events
```bash
# Remove events from last hour (test run)
python db_maintenance.py --remove-recent --hours 1
```

### Fix Categorization
```bash
# Batch update wrong categories
python db_maintenance.py --batch-update --field category --from "Club" --to "Nightlife"
python db_maintenance.py --batch-update --field category --from "Concert" --to "Live Music"
```

### Clean Up After Bad Scrape
```bash
# 1. Identify bad events (compare)
python db_maintenance.py --compare

# 2. Remove recent bad scrape
python db_maintenance.py --remove-recent --hours 3

# 3. Re-scrape correctly
# ... run scraper ...

# 4. Sync good data
python db_maintenance.py --sync-patched
```

## Monitoring

Track all maintenance operations:

```bash
# Log all operations
python db_maintenance.py --sync-patched 2>&1 | tee maintenance.log

# Check for errors
grep "ERROR" maintenance.log

# Count updates
grep "Updated:" maintenance.log
```

## API Reference

### DatabaseMaintenanceTool Class

```python
from db_maintenance import DatabaseMaintenanceTool

tool = DatabaseMaintenanceTool(events_file="all_events.json")

# Update single event
await tool.update_event_by_hash("abc123", {"description": "Fixed"})

# Sync all patched
await tool.update_all_from_local(dry_run=False)

# Remove recent
await tool.remove_recent_events(hours=24, dry_run=True)

# Compare
comparison = await tool.compare_local_vs_db()
```

## Support

For issues:
1. Check `--dry-run` output
2. Verify credentials
3. Check database permissions
4. Review error messages

Part of the Nocturne Event Scraper system.
