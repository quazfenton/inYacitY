# Nocturne Architecture - Data Flow Diagram

## High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                       │
│  - City selector map                                            │
│  - Event cards with live animations                             │
│  - Email subscription form                                      │
│  - Real-time polling during refresh                             │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                 HTTP (REST API)
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
    ┌─────────────────┐          ┌──────────────────┐
    │  FastAPI       │          │   Background     │
    │  Backend       │          │   Task Queue     │
    │                │          │                  │
    │  - /cities     │          │ - Scraper tasks  │
    │  - /events     │          │ - Email sending  │
    │  - /scrape     │          │                  │
    │  - /subscribe  │          │                  │
    └────────┬────────┘          └──────────────────┘
             │
             ├─────────────────────────────────────┐
             ▼                                     ▼
    ┌──────────────────┐              ┌──────────────────┐
    │  Local           │              │  Supabase        │
    │  PostgreSQL      │              │  PostgreSQL      │
    │  (Primary)       │              │  (Shared Cache)  │
    │                  │              │                  │
    │  - Events        │◄────SYNC────►│  - Events        │
    │  - Subscriptions │   (Auto)     │  - Subscriptions │
    │  - Email Logs    │              │                  │
    └──────┬───────────┘              └──────────────────┘
           │
           │ Scraper reads from DB
           │
           ▼
    ┌──────────────────────────────┐
    │  Scraper Module              │
    │  (Python + Playwright)       │
    │                              │
    │  Eventbrite ─┐               │
    │  Meetup ────┼─► all_events   │
    │  Luma ─────┘                 │
    │                              │
    │  Saves to Local DB           │
    │  Triggers Supabase Sync      │
    └──────────────────────────────┘
```

## Event Data Flow (Detailed)

### When User Clicks "REFRESH EVENTS (1/1)"

```
1. FRONTEND
   User clicks button
   POST /scrape/{city}
   Start polling every 1 second
             │
             ▼
2. BACKEND (FastAPI)
   Receive POST /scrape/{city}
   Add to background tasks
   Return immediately
             │
             ▼
3. BACKGROUND SCRAPER
   Fetch events from:
   - Eventbrite API
   - Meetup API  
   - Luma API
   Parse and normalize data
   Filter duplicates by URL
             │
             ▼
4. SAVE TO LOCAL DATABASE
   Check if event exists (by link)
   If yes: Update record
   If no: Insert new record
   Commit transaction
             │
             ▼
5. SYNC TO SUPABASE (if configured)
   For each event:
   - Check if exists
   - Update or insert
   All in parallel
             │
             ▼
6. FRONTEND POLLING
   Every 1 second:
   GET /events/{city}
   Fetch from local DB
   
   Compare with current list:
   If new events: Update UI
   If no changes: Keep polling
   
   After 20 seconds or no new events: Stop
             │
             ▼
7. ANIMATION
   Each new event:
   - Slide up from bottom
   - Fade in
   - 120ms stagger between cards
   - Display: "Found X new events"
             │
             ▼
8. COMPLETION
   Button changes to "REFRESH USED (0/1)"
   Becomes disabled
   Limit persists across cities
```

## Database Schema

### Events Table

```
events
├── id (PK) ─────────────── Unique identifier
├── title ───────────────── Event name
├── link (UNIQUE) ───────── Original event URL (deduplication key)
├── date ────────────────── Event date (YYYY-MM-DD)
├── time ────────────────── Event time (HH:MM)
├── location ─────────────── Venue name and address
├── description ─────────── Event description/details
├── source ──────────────── 'eventbrite', 'meetup', 'luma'
├── city ─────────────── City identifier (e.g., 'ca--los-angeles')
├── synced_at ───────────── When synced to Supabase
├── last_scraped ───────── When event was last found in scrape
└── created_at ──────────── When record was created

Indexes:
├── idx_events_city ─────────── Fast lookup by city
├── idx_events_city_date ───── Filter by date range
└── idx_events_last_scraped ─ Find recently updated
```

### Subscriptions Table

```
subscriptions
├── id (PK) ─────────────── Unique identifier
├── email (UNIQUE+city) ── User email (part of composite key)
├── city ─────────────── City they subscribed to
├── is_active ───────────── Currently subscribed?
├── created_at ──────────── Subscription date
└── unsubscribed_at ───── When they unsubscribed

Indexes:
├── idx_subscriptions_email ──── Find user subscriptions
└── idx_subscriptions_city ───── Find subscribers per city
```

## API Endpoints

### Cities
```
GET /cities
Response:
{
  "cities": [
    {
      "id": "ca--los-angeles",
      "name": "LOS ANGELES",
      "slug": "los-angeles",
      "coordinates": {"lat": 34.0522, "lng": -118.2437}
    },
    ...
  ]
}
```

### Events
```
GET /events/{city}?limit=100&start_date=2026-02-05&end_date=2026-02-12
Response:
[
  {
    "id": 1,
    "title": "Warehouse Rave",
    "link": "https://eventbrite.com/...",
    "date": "2026-02-15",
    "time": "22:00",
    "location": "Downtown LA",
    "description": "Underground electronic music...",
    "source": "eventbrite",
    "city": "ca--los-angeles"
  },
  ...
]
```

### Subscribe
```
POST /subscribe
Request:
{
  "email": "user@example.com",
  "city": "ca--los-angeles"
}
Response:
{
  "id": 1,
  "email": "user@example.com",
  "city": "ca--los-angeles",
  "is_active": true,
  "created_at": "2026-02-05T12:00:00"
}
```

### Scrape (Trigger)
```
POST /scrape/{city}
Response:
{
  "message": "Scraping initiated for ca--los-angeles",
  "city": "ca--los-angeles",
  "note": "Events will be synced to shared database in real-time"
}
```

## Real-Time Data Synchronization

### Without Supabase (Local Only)
```
Scraper 1          Database          Scraper 2
(User A)             (Local)           (User B)
   │                   │                  │
   ├─ Scrape LA ────►  │ Save to LA       │
   │                   │                  │
   │                   │ ─ LA Events      │
   │                   │                  ├─ User B views LA
   │                   │ ◄─ Fetch LA ─────┤
   │                   │   No new events  │
   │                   │   (just user A's) │
```

### With Supabase (Shared)
```
Scraper 1          Local DB          Supabase DB      Scraper 2
(User A)            (Fast)             (Shared)         (User B)
   │                  │                   │                │
   ├─ Scrape LA ────► │                   │                │
   │                  │ Save              │                │
   │                  ├─ Sync ───────────►│                │
   │                  │                   │                │
   │                  │                   │<─ Replicates──┐│
   │                  │ ◄──────────────────┤               ││
   │                  │                   │                ││
   │                  │ LA Events          │                │├─ User B views LA
   │                  │ (User A + Synced)  │                │
   │                  │                   ├─ User B views ─┤
   │                  │                   │   (gets synced) │
```

## Session State Management

### Refresh Limit (1 Per Session)

```
Session Start
│
├─ Navigate to Los Angeles
│  └─ refreshUsed = false
│     Button: "REFRESH EVENTS (1/1)"
│
├─ Click refresh
│  └─ refreshUsed = true
│     Button: "REFRESH USED (0/1)" ← Disabled
│
├─ Navigate to New York
│  └─ refreshUsed = true (still!)
│     Button: "REFRESH USED (0/1)" ← Still disabled
│
├─ Navigate back to Los Angeles
│  └─ refreshUsed = true (persists)
│     Button: "REFRESH USED (0/1)" ← Still disabled
│
└─ Session Ends
   refreshUsed = true (persists across page reloads in same session)
```

## Error Handling

### Scraping Errors

```
Scraper Fails
     │
     ▼
Log Error
Retry with exponential backoff
     │
     ├─ Success? Continue
     │
     └─ Still fail? 
          Return error to polling
          Frontend shows: "Failed to load events"
          User can try again later
```

### Network Errors

```
Frontend Polling
     │
     ├─ Request fails?
     │  └─ Retry on next poll (1 second)
     │     Up to 20 attempts (20 seconds)
     │
     └─ All polls fail?
        └─ Stop polling
           Display last fetched events
           User can manually refresh page
```

### Database Errors

```
Save to Local DB fails
     │
     ├─ Rollback transaction
     │
     ├─ Log error
     │
     ├─ Skip Supabase sync
     │
     └─ Return error (non-blocking)
        Scraper can retry
```

## Performance Characteristics

### Scraping
- **Time**: 5-30 seconds per city (depends on network/scraped data)
- **Throughput**: 100-1000 events per city per run
- **Concurrency**: Sequential per city (can run multiple cities in parallel)

### Frontend Polling
- **Frequency**: 1 event every 1000ms
- **Timeout**: 20 seconds max polling
- **Animation**: 120ms stagger between cards

### Database
- **Query time**: <100ms for 10k events
- **Sync time**: <1s for 100 events to Supabase
- **Storage**: ~1KB per event (all fields)

---

**Architecture Version**: 1.0  
**Last Updated**: February 5, 2026
