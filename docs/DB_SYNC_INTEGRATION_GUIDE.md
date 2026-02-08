# Database Sync Integration Guide

## Overview

This guide explains the complete database synchronization workflow, including event validation, Supabase integration, email subscriptions, and frontend live updates.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        N8N Scheduler                        │
│              (Daily cron rotating through cities)           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │  run.py (Master Scraper Runner)│
        │  - Runs all scrapers           │
        │  - Merges results              │
        │  - Saves to all_events.json    │
        └────────────────┬───────────────┘
                         │
                    Checks run count
                    & SYNC_MODE config
                         │
                         ▼
        ┌────────────────────────────────┐
        │   DatabaseSyncManager          │
        │   (db_sync_enhanced.py)        │
        │                                │
        │  1. Load all_events.json       │
        │  2. Validate & standardize     │
        │  3. Check for duplicates       │
        │  4. Send to Supabase           │
        │  5. Track in event_tracker.json│
        │  6. Empty all_events.json      │
        └────────────────┬───────────────┘
                         │
        ┌────────────────┴───────────────┐
        │                                │
        ▼                                ▼
   Supabase DB              Event Deduplication Tracker
   (events table)           (event_tracker.json)
        │                                │
        └────────────────┬───────────────┘
                         │
                ┌────────┴────────┐
                │                 │
                ▼                 ▼
          Frontend API      Email Notifications
        (Live updates)      (Subscribed users)
```

---

## 1. Configuration Setup

### Update config.json

Add the `DATABASE.SYNC_MODE` configuration:

```json
{
  "DATABASE": {
    "SYNC_MODE": 0,
    "COMMENTS": "0=disabled | 1-4=every Nth run | 5+=every run"
  }
}
```

**Sync Mode Values:**
- `0` - Disabled (no database sync)
- `1` - Sync every run
- `2` - Sync every 2nd run
- `3` - Sync every 3rd run
- `4` - Sync every 4th run
- `5+` - Sync every run (same as 1, but explicit)

**Example Use Cases:**

```json
{
  "DATABASE": {
    "SYNC_MODE": 5
  }
}
```
Syncs to database after every scraper run (frontend always has latest data).

```json
{
  "DATABASE": {
    "SYNC_MODE": 3
  }
}
```
Batches 3 runs of data before syncing (reduces API calls, good for N8N cron jobs).

---

## 2. Environment Setup

Set required environment variables:

```bash
# .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
```

Or export in shell:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your_supabase_anon_key"
```

---

## 3. Database Schema Setup

Create the required tables in Supabase:

### Events Table

```sql
CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  date DATE NOT NULL,
  time TEXT DEFAULT 'TBA',
  location TEXT NOT NULL,
  link TEXT UNIQUE NOT NULL,
  description TEXT,
  source TEXT NOT NULL,
  price INTEGER DEFAULT 0,
  price_tier INTEGER DEFAULT 0,
  category TEXT DEFAULT 'Other',
  event_hash VARCHAR(32) UNIQUE NOT NULL,
  scraped_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- Indexes for common queries
  INDEX idx_date (date),
  INDEX idx_location (location),
  INDEX idx_category (category),
  INDEX idx_price_tier (price_tier),
  );
  CREATE INDEX idx_event_hash ON events (event_hash);
  CREATE INDEX idx_scraped_at ON events (scraped_at);

  ### Email Subscriptions Table
---

## 4. Data Validation & Standardization

The `EventDataValidator` class handles:

### Required Fields
- `title` - Event name
- `date` - Event date (YYYY-MM-DD format)
- `location` - Event location
- `link` - Event URL (must start with http:// or https://)
- `source` - Scraper source (Eventbrite, Luma, Meetup, etc.)

### Optional Fields
- `time` - Event time (defaults to 'TBA')
- `description` - Event description (max 1000 chars)
- `price` - Event price in cents (defaults to 0)

### Automatic Enhancements

**2D Tagging System:**
1. **Price Tier** - Automatically determined from price:
   - 0: Free
   - 1: <$20
   - 2: <$50
   - 3: <$100
   - 4: $100+

2. **Category** - Automatically categorized:
   - Concert, Nightlife, Club, Workshop, Networking
   - Sports, Arts, Food, Community, Tech, Business, Other

**Example:**
```python
from db_sync_enhanced import EventDataValidator

event = {
    "title": "Tech Conference 2026",
    "date": "2026-02-15",
    "location": "San Francisco, CA",
    "link": "https://example.com/event",
    "source": "Eventbrite",
    "price": 4999  # $49.99
}

is_valid, cleaned, errors = EventDataValidator.validate_event(event)

# cleaned will include:
# {
#     "price_tier": 2,  # <$50
#     "category": "Tech",  # Auto-categorized
#     "event_hash": "abc123def456..."  # For deduplication
# }
```

---

## 5. Deduplication Strategy

The system uses multiple layers of deduplication:

### 1. Event Hash (Primary)
```
hash = MD5(title.lower() + '|' + date + '|' + location.lower() + '|' + source)
```
Prevents the same event from being inserted multiple times.

### 2. Database Uniqueness Constraint
The `event_hash` field has a UNIQUE constraint in the database.

### 3. Event Tracker (Local)
`event_tracker.json` maintains a local record of synced events:
```json
{
  "events": {
    "abc123def456...": {
      "title": "Event Title",
      "date": "2026-02-15",
      "added_at": "2026-02-06T12:34:56.789Z"
    }
  },
  "last_updated": "2026-02-06T12:34:56.789Z"
}
```

### 4. Automatic Cleanup
Events older than 30 days are automatically removed from the tracker.

---

## 6. Run.py Integration

### How It Works

1. **run.py** executes all scrapers and saves results to `all_events.json`
2. **Run counter** is tracked in `scraper_run_counter.txt`
3. **Sync decision** is made based on:
   - Current run count
   - `DATABASE.SYNC_MODE` from config.json
4. **If sync needed**, DatabaseSyncManager is invoked
5. **After sync**, all_events.json is emptied

### Code Example

```python
# In run.py

async def main():
    # ... run scrapers ...
    
    # Check sync config
    config = get_config()
    sync_mode = config.get('DATABASE.SYNC_MODE', 0)
    
    # Load run counter
    run_count = int(open("scraper_run_counter.txt").read())
    
    # Determine if we should sync
    should_sync = False
    if sync_mode == 0:
        should_sync = False
    elif 1 <= sync_mode <= 4:
        should_sync = (run_count % sync_mode == 0)
    elif sync_mode >= 5:
        should_sync = True
    
    # Sync if needed
    if should_sync:
        manager = DatabaseSyncManager()
        result = await manager.sync_events()
        
        if result['success']:
            print(f"✓ Synced {result['events_synced']} events")
        else:
            print(f"✗ Sync failed: {result['errors']}")
    
    # Increment run counter
    open("scraper_run_counter.txt", "w").write(str(run_count + 1))
```

### Example Scenarios

**Scenario 1: Daily rotation through 5 cities with batching**

```
Day 1: Run LA scraper (run_count=1) → no sync
Day 2: Run NY scraper (run_count=2) → no sync
Day 3: Run DC scraper (run_count=3) → SYNC ✓ (3 mod 3 = 0)
Day 4: Run Miami scraper (run_count=4) → no sync
Day 5: Run Chicago scraper (run_count=5) → no sync
Day 6: Run LA scraper (run_count=6) → SYNC ✓ (6 mod 3 = 0)
```
Config: `SYNC_MODE: 3`

**Scenario 2: Real-time frontend updates**

```
Every run syncs to Supabase immediately
Frontend receives live event updates
```
Config: `SYNC_MODE: 5` (or 1)

---

## 7. Email Subscriptions

### Database Schema

```sql
-- Email subscriptions table (already defined above)
CREATE TABLE email_subscriptions (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  city VARCHAR(50) NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (email, city)
);
```

### API Endpoints

#### Subscribe to events in a city

```bash
POST /api/scraper/email-subscribe
Content-Type: application/json

{
  "email": "user@example.com",
  "city": "ca--los-angeles"
}

Response:
{
  "success": true,
  "message": "Subscription created for user@example.com in ca--los-angeles",
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

#### Unsubscribe from a specific city

```bash
POST /api/scraper/email-unsubscribe
Content-Type: application/json

{
  "email": "user@example.com",
  "city": "ca--los-angeles"
}

Response:
{
  "success": true,
  "message": "Unsubscribed user@example.com from ca--los-angeles",
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

#### Unsubscribe from all cities

```bash
POST /api/scraper/email-unsubscribe
Content-Type: application/json

{
  "email": "user@example.com"
}

Response:
{
  "success": true,
  "message": "Unsubscribed user@example.com from all cities",
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

### Frontend Integration

```typescript
// src/hooks/useEventSubscription.ts

export function useEventSubscription() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const subscribe = async (email: string, city: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/scraper/email-subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, city })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message);
      }
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to subscribe');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const unsubscribe = async (email: string, city?: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/scraper/email-unsubscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, ...(city && { city }) })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message);
      }
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unsubscribe');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return { subscribe, unsubscribe, isLoading, error };
}
```

---

## 8. Frontend Live Updates

### Manual Sync Trigger

```bash
POST /api/scraper/sync
Content-Type: application/json

{
  "force": false
}

Response:
{
  "success": true,
  "events_synced": 42,
  "new_duplicates_removed": 3,
  "past_events_removed": 5,
  "errors": [],
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

### Sync Status Check

```bash
GET /api/scraper/sync-status

Response:
{
  "configured": true,
  "dedup_stats": {
    "total_tracked": 1000,
    "last_updated": "2026-02-06T12:34:56.789Z"
  },
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

### Health Check

```bash
GET /api/scraper/health

Response:
{
  "status": "healthy",
  "supabase_configured": true,
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

---

## 9. File Structure

```
scraper/
├── run.py                    # Main runner (updated)
├── run_updated.py           # New version with sync integration
├── db_sync.py               # Original version
├── db_sync_enhanced.py      # Enhanced version with all features
├── config.json              # Original config
├── config_sync.json         # Config with DATABASE.SYNC_MODE
├── config_loader.py         # Config loader utility
├── all_events.json          # Scraped events (emptied after sync)
├── event_tracker.json       # Deduplication tracker
├── scraper_run_counter.txt  # Run counter
├── [other scrapers]

backend/api/
├── locations_api.py         # Existing
├── scraper_api.py           # NEW - Email subscriptions & sync endpoints
```

---

## 10. Migration Steps

### Step 1: Update Configuration

Copy or merge `DATABASE.SYNC_MODE` into your existing `config.json`:

```bash
cp config_sync.json config.json
```

Or manually add to config.json:
```json
{
  "DATABASE": {
    "SYNC_MODE": 0
  }
}
```

### Step 2: Update Scraper Runner

Replace `run.py` with `run_updated.py`:

```bash
cp run_updated.py run.py
```

### Step 3: Use Enhanced DB Sync

Replace or alias `db_sync.py`:

```bash
cp db_sync_enhanced.py db_sync.py
```

### Step 4: Create Database Tables

Execute SQL migrations in Supabase:

```sql
-- Events table
CREATE TABLE IF NOT EXISTS events (...)

-- Email subscriptions table
CREATE TABLE IF NOT EXISTS email_subscriptions (...)
```

### Step 5: Setup Environment

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your_supabase_anon_key"
```

### Step 6: Integrate API Endpoints

Add scraper_api.py to your Flask app:

```python
from backend.api.scraper_api import scraper_api

app.register_blueprint(scraper_api)
```

### Step 7: Test

```bash
# Test sync endpoint
curl -X POST http://localhost:5000/api/scraper/sync

# Test email subscription
curl -X POST http://localhost:5000/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","city":"ca--los-angeles"}'

# Check health
curl http://localhost:5000/api/scraper/health
```

---

## 11. Monitoring & Logs

### Check Sync Status

```bash
curl http://localhost:5000/api/scraper/sync-status
```

### View Event Tracker

```bash
cat event_tracker.json
```

### Check Run Counter

```bash
cat scraper_run_counter.txt
```

### Monitor N8N Execution

Set up N8N webhook to call the sync API:

```
POST http://your-api.com/api/scraper/sync
```

After each city rotation or batch.

---

## 12. Common Issues & Troubleshooting

### Issue: "Supabase not configured"

**Solution:** Verify environment variables are set:
```bash
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

### Issue: Events not syncing

**Solution:** Check SYNC_MODE in config:
```python
from config_loader import get_config
config = get_config()
print(config.get('DATABASE.SYNC_MODE'))
```

### Issue: Duplicate events in database

**Solution:** Event hash ensures uniqueness. Check:
1. UNIQUE constraint on `event_hash` column
2. Tracker file: `cat event_tracker.json`

### Issue: API endpoints returning 500

**Solution:** Check Flask logs and Supabase connection:
```bash
curl http://localhost:5000/api/scraper/health
```

---

## 13. Next Steps

1. ✅ Update config.json with DATABASE.SYNC_MODE
2. ✅ Create database tables in Supabase
3. ✅ Set environment variables
4. ✅ Update run.py with sync integration
5. ✅ Register Flask API blueprint
6. ✅ Test endpoints
7. Create frontend email subscription form
8. Setup N8N cron job with city rotation
9. Configure email notification service (optional)
10. Monitor production sync performance

---

## Files Summary

| File | Purpose | Status |
|------|---------|--------|
| `run_updated.py` | Master runner with sync integration | ✅ Created |
| `db_sync_enhanced.py` | Enhanced sync with email subscriptions | ✅ Created |
| `scraper_api.py` | Flask API endpoints | ✅ Created |
| `config_sync.json` | Config with DATABASE.SYNC_MODE | ✅ Created |
| DB Schema (SQL) | Supabase tables | 📋 Provided |

---
