# n8n Workflow - Complete Documentation

## Workflow Overview

**Name**: Nocturne Daily Scraper - Rotating Cities  
**Trigger**: Daily at configurable time (default: midnight UTC)  
**Duration**: ~50 seconds per execution  
**Frequency**: Once per day  
**Cities**: 20 cities rotating (1 per day)

## What It Does

1. **Determines City**: Calculates which city to scrape based on day of year
2. **Triggers Scraper**: Calls backend `/scrape/{city_id}` endpoint
3. **Waits for Completion**: Allows 45 seconds for scraping
4. **Fetches Events**: Retrieves newly scraped events (up to 500)
5. **Transforms Data**: Normalizes event format for databases
6. **Syncs to Supabase**: Inserts events to shared database
7. **Syncs to Notion** (optional): Adds events to Notion database
8. **Notifies via Slack** (optional): Sends completion summary

## Node Breakdown

### 1. Daily Trigger (Cron)
**Type**: Cron Trigger  
**Purpose**: Schedule workflow execution

**Configuration**:
```
- Trigger Type: Every Day
- Hour: 0-23 (0 = midnight)
- Minute: 0-59
```

**Output**:
```json
{
  "timestamp": "2026-02-05T00:00:00.000Z"
}
```

**Use Case**: Run at midnight UTC, adjustable to any time

---

### 2. Set Variables
**Type**: Set Variables  
**Purpose**: Calculate which city to scrape today

**Logic**:
```
Day of Year % Number of Cities = City Index
Day 1 % 20 = 0 → City 0 (Los Angeles)
Day 2 % 20 = 1 → City 1 (New York)
Day 21 % 20 = 0 → City 0 (Los Angeles again)
```

**Variables Created**:
- `cities`: Array of 20 city IDs
- `dayOfYear`: Current day of year (1-365)
- `cityIndex`: Index in cities array
- `cityToScrape`: Selected city ID

**Output**:
```json
{
  "cities": ["ca--los-angeles", "ny--new-york", ...],
  "dayOfYear": 36,
  "cityIndex": 16,
  "cityToScrape": "dc--washington"
}
```

**Customize**: Edit cities array to change rotation

---

### 3. Trigger Backend Scraper
**Type**: HTTP Request (POST)  
**Purpose**: Start scraping process on backend

**Endpoint**:
```
POST {NOCTURNE_API_URL}/scrape/{city_id}
```

**Example**:
```
POST http://localhost:8000/scrape/ca--los-angeles
```

**Headers**:
```
Content-Type: application/json
```

**Response**:
```json
{
  "message": "Scraping initiated for ca--los-angeles",
  "city_id": "ca--los-angeles",
  "note": "Events will be synced to shared database in real-time"
}
```

**Purpose**: Triggers background scraper task (returns immediately)

---

### 4. Wait for Scraper
**Type**: Wait  
**Purpose**: Allow scraper time to fetch events

**Configuration**:
```
- Amount: 45
- Unit: seconds
```

**Why 45 seconds?**
- Most cities scrape in 5-30 seconds
- 45 seconds provides buffer for slow networks
- Can adjust based on testing

**Adjust for**:
- More events in city → increase to 60s
- Fewer events → decrease to 30s
- Very slow network → increase to 90s

---

### 5. Fetch Scraped Events
**Type**: HTTP Request (GET)  
**Purpose**: Retrieve newly scraped events from backend

**Endpoint**:
```
GET {NOCTURNE_API_URL}/events/{city_id}?limit=500
```

**Query Parameters**:
- `limit=500`: Maximum events to fetch (adjustable)
- `start_date=2026-02-05`: Optional date filter
- `end_date=2026-02-12`: Optional date filter

**Response**:
```json
[
  {
    "id": 1,
    "title": "Underground Rave",
    "link": "https://eventbrite.com/...",
    "date": "2026-02-15",
    "time": "22:00",
    "location": "Downtown LA",
    "description": "Electronic music event",
    "source": "eventbrite",
    "city_id": "ca--los-angeles"
  },
  ...
]
```

**Handles**:
- Empty results (no events found)
- Large result sets (up to 500 events)
- Network timeouts

---

### 6. Transform Events for Database
**Type**: Code Node (JavaScript)  
**Purpose**: Normalize events to database format

**Input**: Raw events from API

**Transformation**:
```javascript
{
  title: event.title,
  link: event.link,
  date: event.date,
  time: event.time,
  location: event.location,
  description: event.description,
  source: event.source,
  city_id: city_id,
  synced_at: ISO timestamp,
  last_scraped: today's date
}
```

**Output**: Array of normalized events ready for database insertion

**Why**:
- Ensures consistent schema across sources
- Adds sync metadata (synced_at, last_scraped)
- Prepares for both Supabase and Notion

---

### 7. Sync Events to Supabase
**Type**: HTTP Request (POST)  
**Purpose**: Insert events into Supabase

**Endpoint**:
```
POST {SUPABASE_URL}/rest/v1/events
```

**Headers**:
```
Content-Type: application/json
apikey: {SUPABASE_KEY}
Authorization: Bearer {SUPABASE_KEY}
```

**Body**: Array of transformed events

**Response**:
```json
[
  {
    "id": 12345,
    "title": "Underground Rave",
    "created_at": "2026-02-05T00:00:00Z"
  },
  ...
]
```

**Behavior**:
- Creates new events if link doesn't exist
- Updates existing events if link matches
- Automatically deduplicates via UNIQUE(link) constraint

**Note**: Non-blocking - if this fails, workflow continues

---

### 8. Sync Events to Notion (Optional)
**Type**: Notion Append Database Items  
**Purpose**: Create Notion database rows for events

**Setup Required**:
- Notion integration token
- Database ID
- Field mapping

**Fields Mapped**:
- `title` → Title (text)
- `link` → Link (URL)
- `date` → Date (date)
- `time` → Time (text)
- `location` → Location (text)
- `description` → Description (text)
- `source` → Source (select)
- `city_id` → City (text)

**Optional**: Can be disabled if Notion not used

---

### 9. Build Execution Summary
**Type**: Code Node (JavaScript)  
**Purpose**: Create summary for notification

**Output**:
```json
{
  "city": "ca--los-angeles",
  "eventCount": 42,
  "timestamp": "2026-02-05T00:00:51Z",
  "status": "SUCCESS"
}
```

**Logic**:
- Status = "SUCCESS" if events > 0
- Status = "NO_EVENTS" if 0 events
- Counts events from API response

---

### 10. Slack Notification
**Type**: HTTP Request (POST)  
**Purpose**: Send workflow summary to Slack

**Endpoint**:
```
POST {SLACK_WEBHOOK_URL}
```

**Message Format**:
```
🌙 Nocturne Daily Scrape
City: ca--los-angeles
Events Found: 42
Status: SUCCESS
Time: 2026-02-05T00:00:51Z
```

**Optional**: Can be disabled if Slack not used

---

## Execution Flow

```
00:00:00 - Daily Trigger fires
   ↓
00:00:01 - Set Variables calculates city (DC on day 36)
   ↓
00:00:02 - HTTP POST /scrape/dc--washington
   ↓
00:00:03 - Backend returns 200 OK
   ↓
00:00:04 - Wait 45 seconds...
   ↓
00:00:49 - HTTP GET /events/dc--washington?limit=500
   ↓
00:00:50 - Returns 32 events
   ↓
00:00:50 - Transform events to database format
   ↓
00:00:51 - POST to Supabase (async)
   ↓
00:00:51 - Append to Notion (async, if enabled)
   ↓
00:00:51 - Build summary (32 events, SUCCESS)
   ↓
00:00:52 - Send Slack notification
   ↓
00:00:52 - Workflow completes
```

**Total Time**: ~52 seconds

---

## Configuration Options

### Basic Configuration

**File**: `nocturne-daily-scraper.json`

```json
{
  "parameters": {
    "triggerAtHour": 0,
    "triggerAtMinute": 0
  }
}
```

### Environment Variables

All configuration via env vars (recommended for secrets):

```bash
# Required
NOCTURNE_API_URL=http://localhost:8000

# For Supabase sync
SUPABASE_URL=https://project.supabase.co
SUPABASE_KEY=eyJhbGc...

# For Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# For Notion sync
NOTION_DATABASE_ID=abc123...
NOTION_API_KEY=secret_xyz...
```

### Timing Options

**Change Daily Time**:
```
Default: 00:00 UTC (midnight)
Custom: Any hour/minute combination

Examples:
06:00 = 6 AM UTC
14:30 = 2:30 PM UTC
20:00 = 8 PM UTC
```

**Change Wait Duration**:
Edit "Wait for Scraper" node:
- Slow network: 60-90 seconds
- Normal: 45 seconds
- Fast: 30 seconds

**Change Event Limit**:
Edit "Fetch Scraped Events" URL:
- `limit=100`: Only fetch 100 events
- `limit=500`: Fetch up to 500
- `limit=1000`: Fetch up to 1000

### Change Cities

Edit "Set Variables" node, update cities array:

```javascript
const cities = [
  "ca--los-angeles",
  "ny--new-york",
  "ca--san-francisco",
  // ... add/remove as needed
];
```

---

## Error Handling

### Scraper Fails
**Symptom**: HTTP 500 from backend  
**Impact**: No events fetched, but workflow continues  
**Solution**: Check backend logs, fix issue, manually trigger retry

### No Events Found
**Symptom**: eventCount = 0  
**Impact**: Supabase has no new rows  
**Solution**: Normal if city has no new events, workflow succeeds

### Supabase Connection Fails
**Symptom**: HTTP error from Supabase endpoint  
**Impact**: Events not synced, but workflow continues  
**Solution**: Check credentials, verify Supabase is up, retry

### Notion Sync Fails
**Symptom**: Notion node returns error  
**Impact**: Notion not updated, but Supabase is synced  
**Solution**: Check Notion credentials, verify database ID

### Slack Fails
**Symptom**: Slack notification doesn't arrive  
**Impact**: No notification, but data is synced  
**Solution**: Check webhook URL, verify channel access

---

## Monitoring & Alerts

### Check Execution History

In n8n dashboard:
1. Open workflow
2. Click "Executions" tab
3. See all past runs with status/duration

### Set Success Rate Alert

If you want failure notifications:
1. Add error handler after critical nodes
2. Send Slack on error
3. Include error details for debugging

### Log Execution Data

Optional: Send execution summary to backend:

```javascript
// After "Build Execution Summary" node
// POST to your logging endpoint
{
  workflowName: "Nocturne Daily Scraper",
  execution: summary,
  timestamp: new Date().toISOString()
}
```

---

## Scaling & Optimization

### Current Performance
- **Execution Time**: ~50 seconds
- **API Calls**: 4 (1 scrape trigger, 1 fetch, 1+ syncs)
- **Events Processed**: 0-500 per day

### For Multiple Cities Per Day

Create separate workflows:
- Workflow 1: 6am UTC (West Coast)
- Workflow 2: 2pm UTC (Central)
- Workflow 3: 10pm UTC (East Coast)

### For Faster Execution

Reduce wait time:
```
30 seconds = faster but risk missing events
45 seconds = balanced
60 seconds = safer for slow networks
```

### For High Volume

Add batching:
```javascript
// Group events by source before syncing
const grouped = {
  eventbrite: [...],
  meetup: [...],
  luma: [...]
};

// Sync each batch separately
```

---

## Troubleshooting Guide

| Issue | Cause | Fix |
|-------|-------|-----|
| Workflow never runs | Not activated | Toggle "Activate" switch |
| Wrong city each day | dayOfYear calculation off | Verify system date is correct |
| Events not syncing | Bad credentials | Check SUPABASE_URL/KEY |
| Slack not working | Invalid webhook | Regenerate webhook URL |
| Timeout fetching events | Wait time too short | Increase to 60 seconds |
| Duplicate events in DB | UNIQUE constraint missing | Check Supabase table schema |

---

## Advanced: Custom Logic

### Skip Cities with No Events

Add IF condition after "Fetch Scraped Events":

```javascript
if (eventCount > 0) {
  // Sync to databases
} else {
  // Skip sync, just log
}
```

### Notify Only on Large Scrapes

Conditional Slack:

```javascript
if (eventCount > 50) {
  // Send Slack notification
}
```

### Rotate Cities Differently

Change rotation formula:

```javascript
// Current: dayOfYear % cityCount
// Alternative: dayOfWeek (rotate every 7 days)
// Alternative: manual day mapping
```

### Add Retry Logic

After HTTP requests:

```javascript
if (response.status !== 200) {
  // Retry after delay
  await sleep(5000);
  // Call again
}
```

---

## Integration with Frontend

### Frontend Can Query

With Supabase configured, frontend can:

```javascript
// Fetch all events for a city
GET /events/ca--los-angeles

// Will include events from all scrapers
// Includes those from daily n8n automation
```

### Real-Time Updates

If using Supabase with frontend:

```javascript
// Subscribe to event changes
const subscription = supabase
  .from('events')
  .on('INSERT', payload => {
    // New events appear in real-time
  })
  .subscribe();
```

---

## Maintenance Checklist

**Daily**:
- [ ] Check execution succeeded
- [ ] Review event count
- [ ] Check Slack notification (if enabled)

**Weekly**:
- [ ] Review execution history
- [ ] Check for errors in logs
- [ ] Verify Supabase table size

**Monthly**:
- [ ] Review performance metrics
- [ ] Update cities list if needed
- [ ] Test manual workflow trigger
- [ ] Check API rate limits

---

## Support & Resources

- **n8n Documentation**: https://docs.n8n.io/workflows/
- **n8n Community Forum**: https://community.n8n.io/
- **Nocturne Setup**: See N8N_SETUP.md
- **Nocturne API**: See ARCHITECTURE.md

---

**Workflow Version**: 1.0  
**Last Updated**: February 5, 2026  
**Status**: Production Ready
