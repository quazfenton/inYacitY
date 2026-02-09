# Testing Guide for Nocturne Platform

This guide covers testing all components of the Nocturne platform from backend API to frontend functionality.

## Prerequisites

Ensure all services are running:

```bash
# Using Docker Compose
docker-compose up -d

# Check services are running
docker-compose ps
```

Expected output should show:
- `nocturne_db` - running on port 5432
- `nocturne_backend` - running on port 8000
- `nocturne_frontend` - running on port 5173

## 1. Backend API Testing

### 1.1 Health Check

**Endpoint:** `GET /health`

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T19:00:00.123456",
  "total_events": 0,
  "total_subscribers": 0
}
```

**If this fails:**
- Check backend logs: `docker-compose logs backend`
- Check database connection: `docker exec -it nocturne_db psql -U nocturne -c "SELECT 1"`
- Verify DATABASE_URL in `.env`

### 1.2 Get Cities

**Endpoint:** `GET /cities`

```bash
curl http://localhost:8000/cities
```

**Expected Response:**
```json
{
  "cities": [
    {
      "id": "ca--los-angeles",
      "name": "LOS ANGELES",
      "slug": "los-angeles",
      "coordinates": {
        "lat": 34.0522,
        "lng": -118.2437
      }
    },
    {
      "id": "ny--new-york",
      "name": "NEW YORK",
      "slug": "new-york",
      "coordinates": {
        "lat": 40.7128,
        "lng": -74.006
      }
    }
    // ... more cities
  ]
}
```

**Tests:**
- ✅ Returns 40+ cities
- ✅ Each city has id, name, slug, coordinates
- ✅ All cities are from scraper/config.json

### 1.3 Get Events (Empty Database)

**Endpoint:** `GET /events/{city_id}`

```bash
curl http://localhost:8000/events/ca--los-angeles
```

**Expected Response:** `[]` (empty array)

### 1.4 Subscribe (Email Validation)

**Endpoint:** `POST /subscribe`

```bash
curl -X POST http://localhost:8000/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "city_id": "ca--los-angeles"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "email": "test@example.com",
  "city_id": "ca--los-angeles",
  "created_at": "2026-01-31T19:00:00.123456",
  "is_active": true
}
```

**Tests:**
- ✅ Valid email accepted
- ✅ Duplicate subscription returns error (400)
- ✅ Invalid email format returns error (422)
- ✅ Invalid city_id returns error (404)

**Test duplicate subscription:**
```bash
curl -X POST http://localhost:8000/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "city_id": "ca--los-angeles"
  }'
```

**Expected Response:** 
```json
{
  "detail": "Already subscribed to this city"
}
```

**Test invalid email:**
```bash
curl -X POST http://localhost:8000/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "not-an-email",
    "city_id": "ca--los-angeles"
  }'
```

**Expected Response:** 422 Validation Error

### 1.5 Get Subscriptions

**Endpoint:** `GET /subscriptions`

```bash
curl http://localhost:8000/subscriptions
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "email": "test@example.com",
    "city_id": "ca--los-angeles",
    "created_at": "2026-01-31T19:00:00.123456",
    "is_active": true
  }
]
```

**Tests:**
- ✅ Returns all active subscriptions
- ✅ Filter by city: `curl "http://localhost:8000/subscriptions?city_id=ca--los-angeles"`
- ✅ Include inactive: `curl "http://localhost:8000/subscriptions?active_only=false"`

### 1.6 Unsubscribe

**Endpoint:** `DELETE /subscribe/{subscription_id}`

```bash
curl -X DELETE http://localhost:8000/subscribe/1
```

**Expected Response:**
```json
{
  "message": "Unsubscribed successfully"
}
```

**Verify in database:**
```bash
curl http://localhost:8000/subscriptions
```

The subscription should still appear but `is_active` should be `false`.

### 1.7 Trigger Scraping

**Endpoint:** `POST /scrape/{city_id}`

```bash
curl -X POST http://localhost:8000/scrape/ca--los-angeles
```

**Expected Response:**
```json
{
  "message": "Scraping initiated for ca--los-angeles",
  "city_id": "ca--los-angeles"
}
```

**Check logs:**
```bash
docker-compose logs -f backend
```

You should see scraping progress.

### 1.8 Verify Events After Scraping

Wait for scraping to complete (may take 1-2 minutes), then:

```bash
curl http://localhost:8000/health
```

Check `total_events` is greater than 0.

Then fetch events:

```bash
curl http://localhost:8000/events/ca--los-angeles
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "title": "Free Concert in the Park",
    "link": "https://www.eventbrite.com/e/free-concert",
    "date": "2026-02-05",
    "time": "7:00 PM",
    "location": "Central Park",
    "description": "A free outdoor concert...",
    "source": "eventbrite",
    "city_id": "ca--los-angeles"
  }
  // ... more events
]
```

**Tests:**
- ✅ Events have required fields
- ✅ Date filtering works:
  ```bash
  curl "http://localhost:8000/events/ca--los-angeles?start_date=2026-02-01&end_date=2026-02-07"
  ```
- ✅ Limit parameter works:
  ```bash
  curl "http://localhost:8000/events/ca--los-angeles?limit=5"
  ```

### 1.9 Test All Cities Scraping

**Endpoint:** `POST /scrape/all`

```bash
curl -X POST http://localhost:8000/scrape/all
```

**Expected Response:**
```json
{
  "message": "Scraping initiated for all cities"
}
```

⚠️ **Warning:** This will scrape all 40+ cities and may take 15-30 minutes. Use with caution.

## 2. Frontend Testing

### 2.1 Access Frontend

Open browser: `http://localhost:5173`

**Expected UI:**
- Dark theme with #09090b background
- Acid green (#ccff00) accent colors
- City selector landing page
- "NOCTURNE ///" branding in top-left
- City list with hover effects

### 2.2 Test City Selection

1. Click on a city (e.g., "LOS ANGELES")
2. Verify navigation to city feed view

**Expected Behavior:**
- ✅ Smooth transition/animation
- ✅ City name displayed in header
- ✅ Events loaded (or "NO SIGNAL FOUND" if no events)
- ✅ Back button to return to city selector
- ✅ Subscribe form visible in sidebar
- ✅ VibeChart component visible
- ✅ "SCAN FOR UNDERGROUND" button visible

### 2.3 Test Event Display

If events exist:
- ✅ Events displayed as cards
- ✅ Each card shows title, date, time, location, description
- ✅ Tags displayed (#Techno, #Art, etc.)
- ✅ Price displayed
- ✅ "VIEW" link to original event source
- ✅ Hover effects on cards

If no events:
- ✅ "NO SIGNAL FOUND. INITIATE SCAN." message displayed
- ✅ User can click "SCAN FOR UNDERGROUND" button

### 2.4 Test Subscription Form

1. Enter email: `test@example.com`
2. Click send button

**Expected Behavior:**
- ✅ Loading spinner appears
- ✅ After 1-2 seconds, success message appears
- ✅ Success message: ">> PROTOCOL INITIATED. CHECK INBOX."
- ✅ "RESET" button appears to clear form

**Test Validation:**
1. Enter invalid email: `not-an-email`
2. Try to submit

**Expected Behavior:**
- ✅ Form validation prevents submission
- ✅ Browser's built-in HTML5 validation shows error

**Test Duplicate:**
1. Subscribe with same email and city again
2. Expected: Error message from API displayed

### 2.5 Test Scraping Integration

1. Click "SCAN FOR UNDERGROUND" button
2. Observe loading state

**Expected Behavior:**
- ✅ Button shows "DECRYPTING SIGNAL..." with spinner
- ✅ Button disabled during scraping
- ✅ Events refresh after scraping completes
- ✅ No page reload (smooth update)

### 2.6 Test Responsive Design

Open browser DevTools (F12) and test different screen sizes:

**Mobile (< 768px):**
- ✅ City names stack vertically
- ✅ Coordinates hidden
- ✅ Events feed uses single column
- ✅ Sidebar content stacks above events

**Tablet (768px - 1024px):**
- ✅ Two-column layout for events
- ✅ Sidebar on left

**Desktop (> 1024px):**
- ✅ Hover city images visible
- ✅ Full city list visible
- ✅ Optimized grid layout

### 2.7 Test Navigation

1. Start at landing page (city selector)
2. Select a city
3. Click "RETURN_TO_MAP" button
4. Select different city
5. Click "SCAN FOR UNDERGROUND"
6. Click on event "VIEW" link
7. Click back in browser

**Expected Behavior:**
- ✅ All transitions smooth
- ✅ State maintained correctly
- ✅ No page reloads
- ✅ External links open in new tab
- ✅ Browser back button works

### 2.8 Test About Modal

1. Click "NOCTURNE///" in top-left
2. Modal should appear
3. Click "X" button to close

**Expected Behavior:**
- ✅ Modal appears with backdrop blur
- ✅ Manifesto text visible
- ✅ Subscribe form in modal
- ✅ Close button works
- ✅ Clicking backdrop closes modal

## 3. Integration Testing

### 3.1 End-to-End Flow

1. **Clear database:**
   ```bash
   docker exec -it nocturne_db psql -U nocturne -c "TRUNCATE events, subscriptions, email_logs CASCADE;"
   ```

2. **Open frontend:** `http://localhost:5173`

3. **Select city:** Click "LOS ANGELES"

4. **Subscribe:**
   - Enter email: `test@example.com`
   - Click send
   - Verify success message

5. **Verify subscription in database:**
   ```bash
   curl http://localhost:8000/subscriptions
   ```

6. **Trigger scraping:**
   - Click "SCAN FOR UNDERGROUND"
   - Wait for completion

7. **Verify events in database:**
   ```bash
   curl http://localhost:8000/events/ca--los-angeles | jq '. | length'
   ```

8. **Refresh page and verify events display:**
   - Reload browser
   - Verify events still displayed
   - Verify event cards show correct data

### 3.2 Multi-City Testing

1. Subscribe to multiple cities:
   - Subscribe to "NEW YORK" with `test@example.com`
   - Subscribe to "CHICAGO" with `test@example.com`

2. Verify subscriptions:
   ```bash
   curl http://localhost:8000/subscriptions | jq '.[] | {email, city_id}'
   ```

3. Scrape multiple cities

4. Verify events for each city:
   ```bash
   curl http://localhost:8000/events/ny--new-york | jq '. | length'
   curl http://localhost:8000/events/il--chicago | jq '. | length'
   ```

### 3.3 Error Handling Tests

**Test 1: Invalid city ID**
```bash
curl http://localhost:8000/events/invalid-city
```
Expected: 404 error

**Test 2: Invalid subscription ID**
```bash
curl -X DELETE http://localhost:8000/subscribe/999999
```
Expected: 404 error

**Test 3: Invalid date format**
```bash
curl "http://localhost:8000/events/ca--los-angeles?start_date=invalid"
```
Expected: 422 validation error

**Test 4: Frontend API failure**
1. Stop backend: `docker-compose stop backend`
2. Refresh frontend
3. Select a city
4. Expected: Error handling in UI (check console for errors)

## 4. Email Service Testing

### 4.1 Test SMTP Configuration

```bash
cd backend
python3 -c "
from email_service import send_email
import asyncio

async def test():
    result = await send_email(
        'test@example.com',
        'Test Email from Nocturne',
        'This is a test email.'
    )
    print(f'Email sent: {result}')

asyncio.run(test())
"
```

**Expected:** `True` if email sent successfully

**If fails:**
- Verify SMTP credentials in `.env`
- Check if email provider allows less secure apps (for Gmail, use app password)

### 4.2 Test SendGrid (if configured)

```bash
python3 -c "
from email_service import send_email_sendgrid
import asyncio

async def test():
    result = await send_email_sendgrid(
        'test@example.com',
        'Test Email from Nocturne',
        'This is a test email.'
    )
    print(f'Email sent: {result}')

asyncio.run(test())
"
```

### 4.3 Test Subscription Confirmation

```bash
python3 -c "
from email_service import send_subscription_confirmation
import asyncio

async def test():
    result = await send_subscription_confirmation(
        'test@example.com',
        'LOS ANGELES',
        'ca--los-angeles'
    )
    print(f'Confirmation email sent: {result}')

asyncio.run(test())
"
```

## 5. Scraper Testing

### 5.1 Test Single City Scraping

```bash
cd backend
python3 -c "
from scraper_integration import scrape_city_events
import asyncio

async def test():
    result = await scrape_city_events('ca--los-angeles')
    print(f'Scraped: {result}')

asyncio.run(test())
"
```

**Expected Output:**
```
[2026-01-31 19:00:00] Starting scrape for city: ca--los-angeles
[2026-01-31 19:00:01] Running scrapers for ca--los-angeles...
...
[2026-01-31 19:02:00] Saved 15 new events, updated 2 existing events
```

### 5.2 Test All Cities Scraping

```bash
python3 -c "
from scraper_integration import refresh_all_cities
import asyncio

async def test():
    result = await refresh_all_cities()
    print(f'Refresh result: {result}')

asyncio.run(test())
"
```

⚠️ **Warning:** This scrapes all 40+ cities and takes significant time.

### 5.3 Verify Scraper Output

Check scraper output files:
```bash
ls -la ../scraper/*_events.json
```

Expected:
- `meetup_events.json`
- `luma_events.json`
- `all_events.json`

View sample events:
```bash
cat ../scraper/all_events.json | jq '.events[0]'
```

## 6. Database Testing

### 6.1 Test Database Connection

```bash
docker exec -it nocturne_db psql -U nocturne -c "SELECT version();"
```

**Expected:** PostgreSQL version information

### 6.2 Test Database Tables

```bash
docker exec -it nocturne_db psql -U nocturne -d nocturne -c "\dt"
```

**Expected:**
```
        List of relations
 Schema |    Name     | Type  |  Owner
--------+-------------+-------+----------
 public | email_logs  | table | nocturne
 public | events      | table | nocturne
 public | subscriptions | table | nocturne
```

### 6.3 Test Database Indexes

```bash
docker exec -it nocturne_db psql -U nocturne -d nocturne -c "\di"
```

**Expected:** List of indexes including:
- `idx_events_city_date`
- `uq_email_city`
- `idx_subscriptions_active`

### 6.4 Test Unique Constraints

```bash
docker exec -it nocturne_db psql -U nocturne -d nocturne -c "
INSERT INTO events (title, link, date, time, location, description, source, city_id)
VALUES ('Test Event', 'https://test.com', '2026-02-01', '7:00 PM', 'Test Location', 'Test Desc', 'test', 'ca--los-angeles');

INSERT INTO events (title, link, date, time, location, description, source, city_id)
VALUES ('Test Event 2', 'https://test.com', '2026-02-01', '8:00 PM', 'Test Location 2', 'Test Desc 2', 'test', 'ca--los-angeles');
"
```

**Expected:** Second insert should fail with unique constraint error on `link`.

### 6.5 Cleanup Old Events

```bash
cd backend
python3 -c "
from cron_scraper import cleanup_old_events
import asyncio

asyncio.run(cleanup_old_events())
"
```

## 7. Cron Job Testing

### 7.1 Test Daily Scrape

```bash
python3 cron_scraper.py daily
```

**Expected:**
- Scrapes all cities
- Cleans up old events
- Sends weekly digest if Monday

### 7.2 Test Cleanup Only

```bash
python3 cron_scraper.py cleanup
```

### 7.3 Test Digest Email

```bash
python3 cron_scraper.py digest
```

**Expected:**
- Sends digest email to all active subscribers
- Logs email activity to database

## 8. Performance Testing

### 8.1 API Response Time

```bash
time curl http://localhost:8000/cities
time curl http://localhost:8000/events/ca--los-angeles
```

**Expected:** Responses under 100ms for cities, 200ms for events

### 8.2 Load Testing (Simple)

```bash
# Install Apache Bench if needed
apt-get install apache2-utils

# Test health endpoint
ab -n 100 -c 10 http://localhost:8000/health

# Test events endpoint
ab -n 100 -c 10 http://localhost:8000/events/ca--los-angeles
```

## 9. Security Testing

### 9.1 Test SQL Injection Protection

```bash
curl "http://localhost:8000/events/'; DROP TABLE events; --"
```

**Expected:** 404 error (not SQL injection)

### 9.2 Test XSS Protection

Subscribe with:
```bash
curl -X POST http://localhost:8000/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "<script>alert(1)</script>@example.com",
    "city_id": "ca--los-angeles"
  }'
```

**Expected:** 422 validation error (email format validation)

### 9.3 Test CORS

```bash
curl -H "Origin: http://evil.com" http://localhost:8000/health -I
```

**Expected:** `Access-Control-Allow-Origin: *` header present (for dev; configure strict origins in production)

## 10. Troubleshooting Common Issues

### Issue: Backend won't start

```bash
# Check logs
docker-compose logs backend

# Check database connection
docker exec -it nocturne_db psql -U nocturne -c "SELECT 1"

# Verify environment variables
docker exec -it nocturne_backend env | grep DATABASE_URL
```

### Issue: Frontend can't connect to backend

```bash
# Check VITE_API_URL
docker exec -it nocturne_frontend env | grep VITE_API_URL

# Test backend from frontend container
docker exec -it nocturne_frontend curl http://nocturne_backend:8000/health
```

### Issue: Scraper fails

```bash
# Check Playwright installation
docker exec -it nocturne_backend python3 -c "import playwright; print(playwright.__version__)"

# Test playwright browsers
docker exec -it nocturne_backend playwright install --help

# Check scraper logs
docker-compose logs backend | grep -i error
```

### Issue: Email not sending

```bash
# Test email service directly
docker exec -it nocturne_backend python3 email_service.py

# Check environment variables
docker exec -it nocturne_backend env | grep SMTP
docker exec -it nocturne_backend env | grep SENDGRID
```

## Summary Checklist

- [ ] Backend health check passes
- [ ] Cities endpoint returns 40+ cities
- [ ] Can subscribe/unsubscribe
- [ ] Can scrape single city
- [ ] Events appear in database
- [ ] Frontend loads correctly
- [ ] City selection works
- [ ] Events display properly
- [ ] Subscription form works
- [ ] Scraping refresh button works
- [ ] Email service configured
- [ ] Cron job runs successfully
- [ ] Database indexes created
- [ ] All visual elements preserved
- [ ] Responsive design works
- [ ] Error handling tested
- [ ] Performance acceptable

All tests passing indicates a fully functional Nocturne platform ready for deployment.
