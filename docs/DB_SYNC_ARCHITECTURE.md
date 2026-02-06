# Database Sync Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVENT SCRAPING PIPELINE                    │
└─────────────────────────────────────────────────────────────────┘

                          ┌──────────────────┐
                          │   N8N Scheduler  │
                          │   (Cron Jobs)    │
                          └────────┬─────────┘
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                │
            ┌─────▼───┐      ┌─────▼───┐     ┌─────▼───┐
            │ LA City │      │ NY City │ ... │ SF City │
            └─────┬───┘      └─────┬───┘     └─────┬───┘
                  │                │               │
                  └────────────────┼───────────────┘
                                   │
                        ┌──────────▼────────────┐
                        │  run_all_scrapers()   │
                        │                       │
                        │ Eventbrite, Dice.fm  │
                        │ Luma, Meetup, RA.co  │
                        │ Posh.vip              │
                        └──────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │  all_events.json (raw)   │
                     │                          │
                     │  {                       │
                     │    "events": [...]       │
                     │    "location": "...",    │
                     │    "timestamp": "...",   │
                     │    "sources": {...}      │
                     │  }                       │
                     └──────────┬───────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────┐
              │  Check Run Counter & SYNC_MODE       │
              │                                      │
              │  run_count % sync_mode == 0 ?        │
              └──────────┬───────────────┬───────────┘
                         │               │
                    YES  │               │  NO
                         ▼               ▼
              ┌────────────────┐   ┌──────────────┐
              │  SYNC NEEDED   │   │ SKIP SYNC    │
              └────────┬───────┘   └──────────────┘
                       │
                       ▼
           ┌───────────────────────────────┐
           │  DatabaseSyncManager          │
           │  ├─ Load all_events.json      │
           │  ├─ Validate & Standardize    │
           │  ├─ Check Duplicates          │
           │  ├─ Send to Supabase          │
           │  ├─ Update Tracker            │
           │  └─ Empty all_events.json     │
           └───────────┬───────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
   ┌─────────────┐          ┌──────────────────┐
   │ Supabase DB │          │ event_tracker    │
   │             │          │ (Local JSON)     │
   │ - events    │          │                  │
   │ - subscript │          │ Dedup history    │
   │   ions      │          │ & cleanup        │
   └─────────────┘          └──────────────────┘
        │
        ├──── Triggers ────┐
        │                  │
        ▼                  ▼
   ┌─────────────┐   ┌─────────────┐
   │  Frontend   │   │    Emails   │
   │  API (Live) │   │ (Notify     │
   │             │   │  Subs)      │
   └─────────────┘   └─────────────┘
```

---

## Data Validation Pipeline

```
┌──────────────────────────────────────┐
│         Raw Event from Scraper       │
│                                      │
│  {                                   │
│    "title": "...",                   │
│    "date": "2026-02-15",             │
│    "location": "...",                │
│    "link": "...",                    │
│    "source": "Eventbrite",           │
│    "price": 2500                     │
│  }                                   │
└────────────┬─────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Validate Required  │
    │ Fields             │
    │ (title, date,      │
    │  location, link,   │
    │  source)           │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ Validate Field     │
    │ Formats            │
    │ - date: YYYY-MM-DD │
    │ - link: http(s)    │
    │ - price: integer   │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ Compute 2D Tags    │
    │                    │
    │ 1. Price Tier:     │
    │    Free, <$20,     │
    │    <$50, <$100,    │
    │    $100+           │
    │                    │
    │ 2. Category:       │
    │    Concert,        │
    │    Nightlife,      │
    │    Tech, etc.      │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ Generate Hash      │
    │ for Dedup          │
    │                    │
    │ MD5(title|date|    │
    │     location|      │
    │     source)        │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ Add Metadata       │
    │                    │
    │ - scraped_at       │
    │ - event_hash       │
    │ - price_tier       │
    │ - category         │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ Cleaned Event      │
    │ (Ready for DB)     │
    │                    │
    │ {                  │
    │   ...fields,       │
    │   "price_tier": 2, │
    │   "category":      │
    │     "Concert",     │
    │   "event_hash":    │
    │     "abc123..."    │
    │ }                  │
    └────────────────────┘
```

---

## Deduplication Strategy

```
┌──────────────────────────────────────────────────────────┐
│                  DEDUPLICATION LAYERS                    │
└──────────────────────────────────────────────────────────┘

Input: Event with event_hash = "abc123..."

        │
        ▼
    ┌─────────────────────────────────┐
    │ Layer 1: Local Tracker Check    │
    │                                 │
    │ Is event_hash in                │
    │ event_tracker.json ?            │
    │                                 │
    │ ✓ Prevents duplicate processing │
    │ ✓ Fast local lookup             │
    └─────────────┬───────────────────┘
                  │ Pass (new event)
                  ▼
    ┌─────────────────────────────────┐
    │ Layer 2: Database Lookup        │
    │                                 │
    │ SELECT * FROM events            │
    │ WHERE event_hash = ?            │
    │                                 │
    │ ✓ Prevents duplicates from DB   │
    │ ✓ Detects DB collisions         │
    └─────────────┬───────────────────┘
                  │ Pass (not in DB)
                  ▼
    ┌─────────────────────────────────┐
    │ Layer 3: UNIQUE Constraint      │
    │                                 │
    │ INSERT into events with         │
    │ UNIQUE(event_hash)              │
    │                                 │
    │ ✓ Database enforces uniqueness  │
    │ ✓ Prevents concurrent inserts   │
    └─────────────┬───────────────────┘
                  │ Pass (inserted)
                  ▼
    ┌─────────────────────────────────┐
    │ Layer 4: Tracker Update         │
    │                                 │
    │ Add to event_tracker.json       │
    │ {                               │
    │   "abc123": {                   │
    │     "title": "...",             │
    │     "date": "2026-02-15",       │
    │     "added_at": "2026-02-06..." │
    │   }                             │
    │ }                               │
    │                                 │
    │ ✓ Prevents reprocessing         │
    │ ✓ Enables cleanup of old events │
    └─────────────────────────────────┘
```

---

## Sync Mode Configuration

```
┌──────────────────────────────────────────────────────────┐
│                  SYNC_MODE VALUES                        │
└──────────────────────────────────────────────────────────┘

Scenario 1: SYNC_MODE = 0 (Disabled)
┌──────────────────────────────────────────────────────────┐
│ Run 1 ──X── (no sync)                                    │
│ Run 2 ──X── (no sync)                                    │
│ Run 3 ──X── (no sync)                                    │
│                                                          │
│ Use: Manual control, testing                            │
│ API: /api/scraper/sync (manual trigger)                 │
└──────────────────────────────────────────────────────────┘

Scenario 2: SYNC_MODE = 1 (Every run)
┌──────────────────────────────────────────────────────────┐
│ Run 1 ──✓ SYNC                                           │
│ Run 2 ──✓ SYNC                                           │
│ Run 3 ──✓ SYNC                                           │
│                                                          │
│ Use: Real-time frontend updates                         │
│ Note: More API calls, but always fresh data             │
└──────────────────────────────────────────────────────────┘

Scenario 3: SYNC_MODE = 3 (Every 3rd run)
┌──────────────────────────────────────────────────────────┐
│ Run 1 ──X── (no sync)    [count: 1 % 3 = 1]            │
│ Run 2 ──X── (no sync)    [count: 2 % 3 = 2]            │
│ Run 3 ──✓ SYNC           [count: 3 % 3 = 0] ✓ Sync     │
│ Run 4 ──X── (no sync)    [count: 4 % 3 = 1]            │
│ Run 5 ──X── (no sync)    [count: 5 % 3 = 2]            │
│ Run 6 ──✓ SYNC           [count: 6 % 3 = 0] ✓ Sync     │
│                                                          │
│ Use: Batch collection from 3 cities, then sync          │
│ Example N8N Job:                                        │
│   Day 1: Scrape LA   (run 1)                           │
│   Day 2: Scrape NY   (run 2)                           │
│   Day 3: Scrape DC   (run 3) ──> SYNC to DB            │
│   Day 4: Scrape Miami (run 4)                          │
│   Day 5: Scrape Chicago (run 5)                        │
│   Day 6: Scrape Seattle (run 6) ──> SYNC to DB         │
└──────────────────────────────────────────────────────────┘

Scenario 4: SYNC_MODE = 5 (Every run, explicit)
┌──────────────────────────────────────────────────────────┐
│ Run 1 ──✓ SYNC           [5 >= 5]                       │
│ Run 2 ──✓ SYNC           [5 >= 5]                       │
│ Run 3 ──✓ SYNC           [5 >= 5]                       │
│                                                          │
│ Use: Same as SYNC_MODE=1, but for clarity              │
└──────────────────────────────────────────────────────────┘
```

---

## API Integration Flow

```
┌──────────────────────────────────────────────────────────┐
│                  FRONTEND INTERACTIONS                   │
└──────────────────────────────────────────────────────────┘

User Subscribes to Events in LA
│
├─ Click "Subscribe" button
│
├─ useEventSubscription hook captures:
│   - email: "user@example.com"
│   - city: "ca--los-angeles"
│
├─ POST /api/scraper/email-subscribe
│   {
│     "email": "user@example.com",
│     "city": "ca--los-angeles"
│   }
│
├─ Backend processes:
│   ├─ Validate email format
│   ├─ Check if subscription exists
│   ├─ Insert/update in Supabase
│   └─ Return response
│
├─ Response: 201 Created
│   {
│     "success": true,
│     "message": "Subscription created...",
│     "timestamp": "2026-02-06T12:34:56Z"
│   }
│
└─ Frontend shows success message

---

Admin Manually Triggers Sync
│
├─ Call /api/scraper/sync
│
├─ Backend processes:
│   ├─ Load all_events.json
│   ├─ Validate all events
│   ├─ Check for duplicates
│   ├─ Insert to Supabase
│   ├─ Update tracker
│   └─ Empty all_events.json
│
├─ Response: 200 OK
│   {
│     "success": true,
│     "events_synced": 42,
│     "new_duplicates_removed": 3,
│     "past_events_removed": 5,
│     "errors": []
│   }
│
└─ Frontend updates event list

---

Check Sync Status
│
├─ GET /api/scraper/sync-status
│
├─ Response: 200 OK
│   {
│     "configured": true,
│     "dedup_stats": {
│       "total_tracked": 1000,
│       "last_updated": "2026-02-06T12:00:00Z"
│     },
│     "timestamp": "2026-02-06T12:34:56Z"
│   }
│
└─ Frontend displays tracker stats
```

---

## Database Schema

```
┌─────────────────────────────────────────────────────────┐
│                     EVENTS TABLE                        │
├─────────────────────────────────────────────────────────┤
│ Column          │ Type      │ Constraints              │
├─────────────────┼───────────┼──────────────────────────┤
│ id              │ BIGSERIAL │ PRIMARY KEY              │
│ title           │ TEXT      │ NOT NULL                 │
│ date            │ DATE      │ NOT NULL, INDEX          │
│ time            │ TEXT      │ DEFAULT 'TBA'            │
│ location        │ TEXT      │ NOT NULL, INDEX          │
│ link            │ TEXT      │ UNIQUE NOT NULL          │
│ description     │ TEXT      │ (max 1000 chars)         │
│ source          │ TEXT      │ NOT NULL                 │
│ price           │ INTEGER   │ DEFAULT 0                │
│ price_tier      │ INTEGER   │ (0-4), INDEX             │
│ category        │ TEXT      │ DEFAULT 'Other', INDEX   │
│ event_hash      │ VARCHAR32 │ UNIQUE NOT NULL, INDEX   │
│ scraped_at      │ TIMESTAMP │ NOT NULL                 │
│ created_at      │ TIMESTAMP │ DEFAULT NOW()            │
│ updated_at      │ TIMESTAMP │ DEFAULT NOW()            │
└─────────────────┴───────────┴──────────────────────────┘

Indexes:
  - idx_date (for range queries on event dates)
  - idx_location (for filtering by location)
  - idx_category (for category filtering)
  - idx_price_tier (for price filtering)
  - idx_event_hash (for deduplication)
  - idx_scraped_at (for monitoring sync freshness)

---

┌─────────────────────────────────────────────────────────┐
│              EMAIL_SUBSCRIPTIONS TABLE                  │
├─────────────────────────────────────────────────────────┤
│ Column          │ Type      │ Constraints              │
├─────────────────┼───────────┼──────────────────────────┤
│ id              │ BIGSERIAL │ PRIMARY KEY              │
│ email           │ VARCHAR   │ NOT NULL                 │
│ city            │ VARCHAR   │ NOT NULL                 │
│ is_active       │ BOOLEAN   │ DEFAULT true, INDEX      │
│ created_at      │ TIMESTAMP │ DEFAULT NOW()            │
│ updated_at      │ TIMESTAMP │ DEFAULT NOW()            │
│                 │           │ UNIQUE (email, city)     │
└─────────────────┴───────────┴──────────────────────────┘

Indexes:
  - idx_email (for subscriber lookups)
  - idx_city (for city-based notifications)
  - idx_is_active (for filtering active subscriptions)
```

---

## Error Handling Flow

```
┌──────────────────────────────────────────────────────────┐
│                  ERROR HANDLING PATHS                    │
└──────────────────────────────────────────────────────────┘

Event Validation Fails
├─ Invalid date format
├─ Missing required field
├─ Invalid URL format
└─ Response: 400 Bad Request (with error details)

Supabase Not Configured
├─ Missing SUPABASE_URL env var
├─ Missing SUPABASE_KEY env var
└─ Response: 500 with message

Database Connection Error
├─ Network timeout
├─ Authentication failure
├─ Query syntax error
└─ Response: 500 with error details

Duplicate Event
├─ Event hash already exists in DB
├─ Tracked in event_tracker.json
└─ Action: Skip insertion, count as duplicate

Email Subscription Error
├─ Invalid email format
├─ Database constraint violation
└─ Response: 400 Bad Request

All errors are:
  ✓ Logged to console
  ✓ Returned in API response
  ✓ Included in result['errors'] dict
```

---

## Monitoring & Metrics

```
┌──────────────────────────────────────────────────────────┐
│              MONITORING TOUCHPOINTS                      │
└──────────────────────────────────────────────────────────┘

1. Run Counter
   File: scraper_run_counter.txt
   Content: Integer (1, 2, 3, ...)
   Use: Determine sync frequency

2. Event Tracker
   File: event_tracker.json
   Content: Deduplication history
   Use: Track synced events and cleanup

3. All Events
   File: all_events.json
   Content: Raw scraped events
   Use: Verify data before sync

4. API Endpoints
   GET /api/scraper/health
   GET /api/scraper/sync-status
   Use: Monitor system health

5. Database Tables
   SELECT COUNT(*) FROM events
   SELECT COUNT(*) FROM email_subscriptions
   Use: Monitor data growth
```

---

## Performance Characteristics

```
Event Processing Speed
├─ Validation: ~1ms per event
├─ Hash generation: ~0.5ms per event
├─ Category detection: ~2ms per event
└─ Total: ~3.5ms per event

Batch Operations
├─ Batch size: 100 events
├─ Insertion time: ~200-500ms per batch
├─ Network overhead: ~100ms per batch
└─ Total: ~300-600ms per batch

Deduplication Performance
├─ Local tracker lookup: O(1) - instant
├─ Database query: O(log n) with index
├─ File I/O: ~50ms per operation
└─ Memory: ~1MB per 1000 tracked events

Scalability
├─ Events per run: 100-1000
├─ Batch sync time: 1-10 seconds
├─ Memory usage: Minimal (<100MB)
├─ Database growth: ~10-50KB per event
└─ Supports: 10,000+ events, 1000+ subscriptions
```

---

## Integration Checklist

- [ ] Copy db_sync_enhanced.py → db_sync.py
- [ ] Copy run_updated.py → run.py
- [ ] Add DATABASE.SYNC_MODE to config.json
- [ ] Set SUPABASE_URL and SUPABASE_KEY env vars
- [ ] Create events table in Supabase
- [ ] Create email_subscriptions table
- [ ] Register scraper_api blueprint in Flask
- [ ] Test /api/scraper/health endpoint
- [ ] Test /api/scraper/sync endpoint
- [ ] Test /api/scraper/email-subscribe endpoint
- [ ] Run test_db_sync.py validation
- [ ] Deploy to production
- [ ] Monitor initial syncs
- [ ] Setup email notifications (optional)
- [ ] Create frontend subscription form

---
