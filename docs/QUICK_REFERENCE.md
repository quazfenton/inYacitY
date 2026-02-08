# Nocturne Platform - Quick Reference

## Essential Commands

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Start with build
docker-compose up -d --build

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Execute command in container
docker-compose exec backend bash
docker-compose exec postgres psql -U nocturne

# Check service status
docker-compose ps
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U nocturne -d nocturne

# Quick queries
docker-compose exec postgres psql -U nocturne -d nocturne -c "SELECT COUNT(*) FROM events;"
docker-compose exec postgres psql -U nocturne -d nocturne -c "SELECT COUNT(*) FROM subscriptions;"

# View recent events
docker-compose exec postgres psql -U nocturne -d nocturne -c "SELECT title, date, source FROM events ORDER BY date DESC LIMIT 10;"

# View subscriptions
docker-compose exec postgres psql -U nocturne -d nocturne -c "SELECT email, city_id, is_active FROM subscriptions;"

# Clear all data (use with caution!)
docker-compose exec postgres psql -U nocturne -d nocturne -c "TRUNCATE events, subscriptions, email_logs CASCADE;"
```

### Backend API

```bash
# Health check
curl http://localhost:8000/health

# Get all cities
curl http://localhost:8000/cities | jq

# Get events for city
curl http://localhost:8000/events/ca--los-angeles | jq

# Get events with date filter
curl "http://localhost:8000/events/ca--los-angeles?start_date=2026-02-01&end_date=2026-02-07&limit=20" | jq

# Subscribe
curl -X POST http://localhost:8000/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "city_id": "ca--los-angeles"}'

# View all subscriptions
curl http://localhost:8000/subscriptions | jq

# Unsubscribe
curl -X DELETE http://localhost:8000/subscribe/1

# Trigger scraping
curl -X POST http://localhost:8000/scrape/ca--los-angeles

# Scrape all cities (long operation!)
curl -X POST http://localhost:8000/scrape/all
```

### Scraping Operations

```bash
# Scrape single city (via backend)
docker-compose exec backend python3 -c "
from scraper_integration import scrape_city_events
import asyncio
asyncio.run(scrape_city_events('ca--los-angeles'))
"

# Scrape all cities (via backend)
docker-compose exec backend python3 -c "
from scraper_integration import refresh_all_cities
import asyncio
asyncio.run(refresh_all_cities())
"

# Direct scraper execution
cd scraper
python3 run.py

# Test specific scraper
python3 meetup.py
python3 luma.py
```

### Scheduled Tasks

```bash
# Daily scrape + cleanup + weekly digest
cd backend
python3 cron_scraper.py daily

# Cleanup old events only
python3 cron_scraper.py cleanup

# Send weekly digest only
python3 cron_scraper.py digest

# View cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

### Email Testing

```bash
# Test SMTP email
docker-compose exec backend python3 -c "
from email_service import send_email
import asyncio
asyncio.run(send_email('test@example.com', 'Test Subject', 'Test body'))
"

# Test SendGrid
docker-compose exec backend python3 -c "
from email_service import send_email_sendgrid
import asyncio
asyncio.run(send_email_sendgrid('test@example.com', 'Test Subject', 'Test body'))
"

# Test subscription confirmation
docker-compose exec backend python3 -c "
from email_service import send_subscription_confirmation
import asyncio
asyncio.run(send_subscription_confirmation('test@example.com', 'LOS ANGELES', 'ca--los-angeles'))
"
```

### Frontend Development

```bash
# Install dependencies
cd fronto
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npx tsc --noEmit
```

## Configuration Files

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://nocturne:nocturne@localhost:5432/nocturne

# Frontend
VITE_API_URL=http://localhost:8000

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@nocturne.events

# Email (SendGrid)
SENDGRID_API_KEY=SG.your-key
SENDGRID_FROM_EMAIL=noreply@nocturne.events

# Scraper fallback APIs
FIRECRAWL_API_KEY=your-key
HYPERBROWSER_API_KEY=your-key
BROWSERBASE_API_KEY=your-key
ANCHOR_BROWSER_API_KEY=your-key
```

### Key File Locations

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI application |
| `backend/database.py` | SQLAlchemy models |
| `backend/scraper_integration.py` | Scraper bridge |
| `backend/email_service.py` | Email system |
| `fronto/App.tsx` | React main component |
| `fronto/services/apiService.ts` | API client |
| `fronto/constants.ts` | City mappings |
| `scraper/config.json` | Scraper configuration |
| `docker-compose.yml` | Service orchestration |
| `nginx.conf` | Reverse proxy config |

## URLs and Ports

| Service | URL | Port |
|----------|-----|------|
| Frontend | http://localhost:5173 | 5173 |
| Backend API | http://localhost:8000 | 8000 |
| API Docs | http://localhost:8000/docs | 8000 |
| PostgreSQL | localhost:5432 | 5432 |
| Redis (if used) | localhost:6379 | 6379 |

## City IDs

Common city IDs for testing:

- `ca--los-angeles` - Los Angeles
- `ny--new-york` - New York
- `dc--washington` - Washington DC
- `tx--houston` - Houston
- `il--chicago` - Chicago
- `fl--miami` - Miami
- `wa--seattle` - Seattle
- `co--denver` - Denver
- `nv--las-vegas` - Las Vegas
- `tx--austin` - Austin

Full list in `scraper/config.json` or `fronto/constants.ts`.

## Database Schema

### Events Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| title | String(500) | Event title |
| link | String(1000) | Event URL (unique) |
| date | Date | Event date |
| time | String(100) | Event time |
| location | String(500) | Venue/location |
| description | Text | Event description |
| source | String(50) | Source (eventbrite/meetup/luma) |
| city_id | String(100) | City identifier |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update |

### Subscriptions Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| email | String(255) | Subscriber email |
| city_id | String(100) | City ID |
| is_active | Boolean | Active status |
| created_at | DateTime | Subscription date |
| unsubscribed_at | DateTime | Unsubscribe date |

**Unique constraint:** email + city_id

## API Response Examples

### Health Check
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T19:00:00.123456",
  "total_events": 150,
  "total_subscribers": 25
}
```

### Cities Response
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
    }
  ]
}
```

### Events Response
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
]
```

### Subscription Response
```json
{
  "id": 1,
  "email": "test@example.com",
  "city_id": "ca--los-angeles",
  "created_at": "2026-01-31T19:00:00.123456",
  "is_active": true
}
```

## Troubleshooting Quick Fixes

### Backend not responding

```bash
# Check if running
docker-compose ps backend

# Restart backend
docker-compose restart backend

# Check logs
docker-compose logs backend

# Check database connection
docker-compose exec postgres psql -U nocturne -c "SELECT 1;"
```

### Frontend can't connect to backend

```bash
# Check VITE_API_URL
docker-compose exec frontend env | grep VITE_API_URL

# Test backend from frontend container
docker-compose exec frontend curl http://backend:8000/health

# Restart frontend
docker-compose restart frontend
```

### Database connection failed

```bash
# Check PostgreSQL
docker-compose ps postgres

# Connect directly
docker-compose exec postgres psql -U nocturne -d nocturne

# Restart postgres
docker-compose restart postgres

# Check DATABASE_URL in backend
docker-compose exec backend env | grep DATABASE_URL
```

### Scraper fails

```bash
# Check Playwright
docker-compose exec backend python3 -c "import playwright; print(playwright.__version__)"

# Install browsers
docker-compose exec backend playwright install --with-deps chromium

# Run scraper directly
docker-compose exec backend python3 -c "
import sys
sys.path.insert(0, '/app/scraper')
from run import run_all_scrapers
import asyncio
asyncio.run(run_all_scrapers())
"
```

### Email not sending

```bash
# Test email service
docker-compose exec backend python3 email_service.py

# Check SMTP credentials
docker-compose exec backend env | grep SMTP

# Check SendGrid
docker-compose exec backend env | grep SENDGRID

# Test SMTP connection
docker-compose exec backend python3 -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
# Check for errors
s.quit()
"
```

### Port already in use

```bash
# Find process using port
lsof -i :8000
lsof -i :5173

# Kill process
kill -9 <PID>

# OR stop conflicting services
docker-compose down
```

### Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes

# Clean old logs
find /var/log -name "*.log" -mtime +7 -delete

# Clean old backups
find /backups -name "*.sql.gz" -mtime +30 -delete
```

## Cron Job Examples

### Daily scraping at 2 AM
```cron
0 2 * * * cd /home/workspace/inyAcity && docker-compose exec -T backend python3 cron_scraper.py daily >> /var/log/nocturne.log 2>&1
```

### Weekly cleanup on Sundays at 3 AM
```cron
0 3 * * 0 cd /home/workspace/inyAcity && docker-compose exec -T backend python3 cron_scraper.py cleanup >> /var/log/nocturne.log 2>&1
```

### Backup database daily at 4 AM
```cron
0 4 * * * pg_dump -h localhost -U nocturne nocturne | gzip > /backups/nocturne_$(date +\%Y\%m\%d).sql.gz
```

### SSL certificate renewal weekly
```cron
0 5 * * 0 certbot renew --quiet && docker-compose restart nginx
```

## Performance Monitoring

### Database Query Performance
```bash
docker-compose exec postgres psql -U nocturne -d nocturne -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;"
```

### Database Size
```bash
docker-compose exec postgres psql -U nocturne -d nocturne -c "
SELECT pg_size_pretty(pg_database_size('nocturne'));"

docker-compose exec postgres psql -U nocturne -d nocturne -c "
SELECT 
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Docker Container Stats
```bash
docker stats
docker-compose exec backend top
docker-compose exec frontend top
```

## Git Workflow (if using version control)

```bash
# Clone repository
git clone <repository-url>
cd inyAcity

# Create feature branch
git checkout -b feature/your-feature

# Stage changes
git add .

# Commit
git commit -m "Add your feature"

# Push to remote
git push origin feature/your-feature

# Merge to main
git checkout main
git merge feature/your-feature
git push origin main
```

## Common Development Tasks

### Add new city to scraper

1. Edit `scraper/config.json`:
```json
{
  "SUPPORTED_LOCATIONS": [
    "tx--san-antonio",
    "new--city"
  ]
}
```

2. Add mapping to `backend/scraper_integration.py`:
```python
CITY_MAPPING = {
    'new--city': {
        'id': 'new--city',
        'name': 'NEW CITY',
        'slug': 'new-city',
        'coordinates': {'lat': 0.0, 'lng': 0.0}
    }
}
```

3. Add mapping to `fronto/constants.ts`:
```typescript
'new--city': {
    id: 'new--city',
    name: 'NEW CITY',
    slug: 'new-city',
    coordinates: { lat: 0.0, lng: 0.0 }
}
```

### Add new API endpoint

1. Edit `backend/main.py`:
```python
@app.get("/custom-endpoint")
async def custom_endpoint(db=Depends(get_db)):
    # Your logic here
    return {"message": "Success"}
```

2. Test endpoint:
```bash
curl http://localhost:8000/custom-endpoint
```

### Add new frontend component

1. Create component file: `fronto/components/NewComponent.tsx`
2. Import in `fronto/App.tsx`:
```typescript
import NewComponent from './components/NewComponent';
```
3. Use component in JSX: `<NewComponent />`

## Emergency Recovery

### Restore from backup

```bash
# Stop backend to prevent writes
docker-compose stop backend

# Restore database
gunzip < /backups/nocturne_20260131.sql.gz | \
  docker-compose exec -T postgres psql -U nocturne nocturne

# Restart backend
docker-compose start backend
```

### Reset everything (nuclear option)

⚠️ **WARNING:** This deletes all data!

```bash
# Stop services
docker-compose down

# Remove volumes (deletes all data!)
docker-compose down -v

# Start fresh
docker-compose up -d

# Initialize database
docker-compose exec backend python3 -c "from database import init_db; init_db()"
```

## Documentation Index

| Document | Purpose |
|----------|---------|
| `README.md` | Main setup and usage guide |
| `QUICK_REFERENCE.md` | This file - command reference |
| `TESTING_GUIDE.md` | Comprehensive testing procedures |
| `DEPLOYMENT_GUIDE.md` | Production deployment instructions |
| `INTEGRATION_IMPLEMENTATION_SUMMARY.md` | Integration details |
| `FINAL_IMPLEMENTATION_SUMMARY.md` | Complete project summary |
| `IMPLEMENTATION_PLAN.md` | Original planning |
| `TECHNICAL_IMPLEMENTATION_PLAN.md` | Technical architecture |
| `IMPLEMENTATION_TASKS_TIMELINE.md` | Development phases |
| `POTENTIAL_CHALLENGES_SOLUTIONS.md` | Risk mitigation |

---

**Last Updated:** January 31, 2026
**Version:** 1.0.0
**Status:** Production Ready ✅
