# Production Setup Guide - Complete Integration

## Overview

This guide walks through integrating all features into a production-ready system:
- Event scraping with database sync
- Email subscriptions
- Event RSVPs with calendar integration
- Event comments with rate limiting
- Geolocation support

---

## Architecture

```
Frontend (React/TypeScript)
    ↓
Backend API (Flask + Blueprints)
    ├── /api/scraper/* (sync, RSVP, comments, subscriptions)
    └── /api/locations/* (geolocation)
    ↓
Supabase (PostgreSQL)
    ├── events table
    ├── email_subscriptions table
    ├── rsvps table
    └── comments table
    ↓
External (N8N, Email Service)
    ├── Cron jobs (scraper)
    └── Email notifications
```

---

## Part 1: Backend Setup

### 1.1 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- Flask
- Flask-CORS
- supabase
- python-dotenv
- requests
- (others from existing requirements)

### 1.2 Environment Variables

Create `.env` in project root:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here

# Flask
FLASK_ENV=production
FLASK_APP=backend/app.py

# Frontend URL (for CORS)
FRONTEND_URL=https://yourdomain.com

# Scraper Config (optional)
DATABASE_SYNC_MODE=5
```

### 1.3 Create Flask App

Already created: `backend/app.py`

Features:
- Registers all blueprints
- CORS configuration
- Health check endpoint
- Error handlers

### 1.4 Database Setup

**Run in Supabase SQL Editor:**

File 1: `scraper/db_sync_enhanced.py` (already syncs events)

File 2: `backend/models/COMMENTS_DATABASE_SCHEMA.sql`
```sql
CREATE TABLE IF NOT EXISTS comments (...)
-- Copy entire file into Supabase
```

File 3: `scraper/RSVP_DATABASE_SCHEMA.sql`
```sql
CREATE TABLE IF NOT EXISTS rsvps (...)
-- Copy entire file into Supabase
```

File 4: Email subscriptions (created automatically by db_sync)

Or use migration runner:
```bash
python backend/migrations.py
```

---

## Part 2: API Integration

### 2.1 Scraper API Endpoints

All endpoints are in `backend/api/scraper_api.py`

**Email Subscriptions:**
- `POST /api/scraper/email-subscribe`
- `POST /api/scraper/email-unsubscribe`

**RSVPs (NEW):**
- `POST /api/scraper/rsvp`
- `DELETE /api/scraper/rsvp/{rsvp_id}`
- `GET /api/scraper/rsvp-status/{event_id}`

**Comments (NEW):**
- `GET /api/scraper/comments/{event_id}`
- `POST /api/scraper/comments`
- `DELETE /api/scraper/comments/{comment_id}`
- `POST /api/scraper/comments/{comment_id}/like`
- `GET /api/scraper/comments/rate-limit/status`

**Database Sync:**
- `POST /api/scraper/sync`
- `GET /api/scraper/sync-status`

**Health:**
- `GET /api/scraper/health`
- `GET /health`
- `GET /`

### 2.2 Running the Backend

Development:
```bash
python backend/app.py
# or
flask run --host 0.0.0.0 --port 5000
```

Production (with Gunicorn):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:create_app()
```

---

## Part 3: Frontend Integration

### 3.1 Install Hooks

Copy to frontend project:
- `fronto/src/hooks/useEventRSVP.ts`
- `fronto/src/hooks/useEventComments.ts`

### 3.2 API Configuration

Create `fronto/src/config/api.ts`:

```typescript
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const API_ENDPOINTS = {
  // Subscriptions
  subscribeEmail: `${API_BASE}/api/scraper/email-subscribe`,
  unsubscribeEmail: `${API_BASE}/api/scraper/email-unsubscribe`,
  
  // RSVPs
  rsvp: `${API_BASE}/api/scraper/rsvp`,
  rsvpStatus: (eventId: string) => `${API_BASE}/api/scraper/rsvp-status/${eventId}`,
  
  // Comments
  comments: (eventId: string) => `${API_BASE}/api/scraper/comments/${eventId}`,
  postComment: `${API_BASE}/api/scraper/comments`,
  deleteComment: (id: string) => `${API_BASE}/api/scraper/comments/${id}`,
  likeComment: (id: string) => `${API_BASE}/api/scraper/comments/${id}/like`,
  rateLimitStatus: `${API_BASE}/api/scraper/comments/rate-limit/status`,
  
  // Sync
  sync: `${API_BASE}/api/scraper/sync`,
  syncStatus: `${API_BASE}/api/scraper/sync-status`,
};
```

### 3.3 Component Integration

**Event Details Page:**

```typescript
import { useEventRSVP } from '@/hooks/useEventRSVP';
import { useEventComments } from '@/hooks/useEventComments';

export function EventDetails({ eventId }: { eventId: string }) {
  const { rsvpEvent, getRSVPStatus } = useEventRSVP();
  const { fetchComments, postComment, comments } = useEventComments();
  
  useEffect(() => {
    fetchComments(eventId);
    getRSVPStatus(eventId);
  }, [eventId]);
  
  return (
    <div className="event-details">
      {/* Event info */}
      <EventInfo event={event} />
      
      {/* RSVP section */}
      <RSVPSection 
        event={event}
        onRSVP={(data) => rsvpEvent(event, data)}
      />
      
      {/* Comments section */}
      <CommentsSection
        eventId={eventId}
        comments={comments}
        onPostComment={(name, text) => postComment(eventId, name, text)}
      />
    </div>
  );
}
```

### 3.4 Environment Variables

Create `.env`:

```bash
REACT_APP_API_URL=http://localhost:5000
# or for production:
REACT_APP_API_URL=https://api.yourdomain.com
```

---

## Part 4: Database Synchronization

### 4.1 Config Setup

Update `scraper/config.json`:

```json
{
  "DATABASE": {
    "SYNC_MODE": 5
  }
}
```

### 4.2 Manual Sync

```bash
cd scraper
python run.py
```

Or via API:
```bash
curl -X POST http://localhost:5000/api/scraper/sync
```

### 4.3 N8N Automation

Setup daily cron job in N8N:

```
Schedule (daily at 00:00 UTC)
  ↓
Loop through cities (LA, NY, DC, Miami, Chicago, ...)
  ↓
Execute: python scraper/run.py --location {city}
  ↓
Trigger: POST /api/scraper/sync
  ↓
Send Slack notification with results
```

---

## Part 5: Deployment

### 5.1 Docker Setup

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "backend.app:create_app()"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_KEY: ${SUPABASE_KEY}
      FLASK_ENV: production
      FRONTEND_URL: ${FRONTEND_URL}
    volumes:
      - ./scraper:/app/scraper
    restart: always
```

### 5.2 Heroku Deployment

```bash
# Create Procfile
echo "web: gunicorn -w 4 -b 0.0.0.0:\$PORT backend.app:create_app()" > Procfile

# Deploy
heroku create your-app-name
heroku config:set SUPABASE_URL=your_url
heroku config:set SUPABASE_KEY=your_key
git push heroku main
```

### 5.3 Vercel/Netlify (Frontend)

```bash
cd fronto

# .env.production
REACT_APP_API_URL=https://api.yourdomain.com

npm run build
# Deploy build/ folder
```

---

## Part 6: Testing

### 6.1 Backend Tests

```bash
# Test health
curl http://localhost:5000/health

# Test API info
curl http://localhost:5000/

# Test email subscription
curl -X POST http://localhost:5000/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","city":"ca--los-angeles"}'

# Test RSVP
curl -X POST http://localhost:5000/api/scraper/rsvp \
  -H "Content-Type: application/json" \
  -d '{
    "event_id":"test_event",
    "title":"Test Event",
    "date":"2026-02-15",
    "location":"LA",
    "user_name":"John"
  }'

# Test comment
curl -X POST http://localhost:5000/api/scraper/comments \
  -H "Content-Type: application/json" \
  -d '{
    "event_id":"test_event",
    "author_name":"John",
    "text":"Great event!"
  }'

# Check rate limit
curl http://localhost:5000/api/scraper/comments/rate-limit/status
```

### 6.2 Frontend Tests

```bash
# Start dev server
cd fronto
npm start

# Test endpoints in browser console
const res = await fetch('http://localhost:5000/health');
const data = await res.json();
console.log(data);

# Test each hook
import { useEventRSVP } from '@/hooks/useEventRSVP';
import { useEventComments } from '@/hooks/useEventComments';
```

---

## Part 7: Monitoring & Maintenance

### 7.1 Health Checks

Endpoint: `GET /health`

Setup monitoring (DataDog, New Relic, etc.):
```
Every 5 minutes: GET /health
Alert if status != "healthy"
```

### 7.2 Database Monitoring

```sql
-- Check comments table size
SELECT 
  COUNT(*) as total_comments,
  COUNT(CASE WHEN is_approved = true THEN 1 END) as approved,
  COUNT(CASE WHEN is_deleted = false THEN 1 END) as active
FROM comments;

-- Check events synced today
SELECT COUNT(*) 
FROM events 
WHERE DATE(created_at) = CURRENT_DATE;

-- Check rate limit abuse
SELECT author_ip, COUNT(*) as comment_count
FROM comments
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY author_ip
ORDER BY comment_count DESC
LIMIT 10;
```

### 7.3 Logging

All API endpoints log to stdout. Setup centralized logging:
- Datadog
- CloudWatch
- ELK Stack
- etc.

### 7.4 Backup

```bash
# Supabase backup (automatic, set in console)
# Or manual:
pg_dump -h db.supabase.co -U postgres -d postgres > backup.sql
```

---

## Part 8: Production Checklist

### Before Deployment

- [ ] Environment variables configured
- [ ] Supabase tables created (run migrations)
- [ ] Backend tested locally
- [ ] Frontend tested with API
- [ ] Rate limiting working
- [ ] CORS configured for frontend
- [ ] Error handling tested
- [ ] Database backups enabled
- [ ] Monitoring setup

### Deployment Day

- [ ] Deploy backend
- [ ] Test all endpoints
- [ ] Deploy frontend
- [ ] Test in browser
- [ ] Monitor logs
- [ ] Setup N8N automation
- [ ] Send notifications when ready

### Post-Deployment

- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify rate limiting working
- [ ] Check database growth
- [ ] Test email notifications
- [ ] Document any issues

---

## Troubleshooting

### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list | grep -i flask

# Check imports
python -c "from backend.app import create_app; print('OK')"

# Check Supabase connection
python -c "from db_sync_enhanced import SupabaseSync; s = SupabaseSync(); print(s.is_configured())"
```

### Comments Rate Limiting Not Working

```bash
# Check IP is being tracked
curl http://localhost:5000/api/scraper/comments/rate-limit/status

# Test rate limiting (spam 4 comments in 10 seconds)
for i in {1..4}; do
  curl -X POST http://localhost:5000/api/scraper/comments \
    -H "Content-Type: application/json" \
    -d '{"event_id":"test","author_name":"spam","text":"spam'$i'"}'
  sleep 0.5
done
# 4th should return 429
```

### Frontend Can't Reach Backend

```bash
# Check CORS
curl -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS http://localhost:5000/api/scraper/comments

# Check API URL
cat fronto/.env | grep REACT_APP_API_URL

# Test directly
curl http://localhost:5000/api/scraper/health
```

---

## Documentation Links

- **Sync**: DB_SYNC_INTEGRATION_GUIDE.md
- **RSVP**: RSVP_INTEGRATION_GUIDE.md
- **Comments**: COMMENTS_INTEGRATION_GUIDE.md
- **Architecture**: DB_SYNC_ARCHITECTURE.md
- **Deployment**: DEPLOYMENT_GUIDE.md

---

## Support

For issues:
1. Check logs
2. Review relevant documentation
3. Test endpoints with curl
4. Check environment variables
5. Verify database tables exist

---

**Ready for Production** ✅
