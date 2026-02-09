# Nocturne - Underground Event Discovery Platform

Full-stack event discovery platform integrating a React frontend with a Python/ FastAPI backend that scrapes events from Eventbrite, Meetup, and Luma for 40+ US cities.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                          │
│  React 19 + TypeScript + Vite + Tailwind CSS            │
│  Location: fronto/                                        │
└────────────────────────┬────────────────────────────────────┘
                     │ REST API
                     │
┌────────────────────────▼────────────────────────────────────┐
│                    Backend                               │
│  FastAPI + SQLAlchemy + PostgreSQL                       │
│  Location: backend/                                     │
│                                                         │
│  ├── main.py              - FastAPI app & endpoints      │
│  ├── database.py           - SQLAlchemy models            │
│  ├── scraper_integration.py - Connects scraper to DB      │
│  └── email_service.py      - Email notifications        │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │
┌───────────────────────▼───────────────────────────────────┐
│                   Scraper Layer                           │
│  Location: scraper/                                      │
│                                                         │
│  ├── scrapeevents.py      - Eventbrite scraper           │
│  ├── meetup.py            - Meetup.com scraper           │
│  ├── luma.py              - Luma.lu scraper             │
│  ├── run.py               - Master runner                │
│  └── config.json          - City & source config        │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Frontend
- **City Selection**: Interactive landing page with 40+ US cities
- **Event Feed**: Real-time event listings with filtering
- **Email Subscription**: Functional subscription form with validation
- **Responsive Design**: Mobile-first with dark theme aesthetic
- **Smooth Animations**: Transitions, hover effects, loading states
- **Visual Identity**: Maintains the "Nocturne" underground aesthetic

### Backend
- **RESTful API**: FastAPI with async support
- **Database**: PostgreSQL with async SQLAlchemy ORM
- **Event Storage**: Centralized storage for all scraped events
- **Subscription Management**: Email subscriptions with city-specific lists
- **Background Tasks**: Scheduled scraping via cron jobs

### Scraper
- **Multi-Source**: Scrapes Eventbrite, Meetup, and Luma
- **Anti-Bot Detection**: Pydoll browser automation with CAPTCHA handling
- **Fallback APIs**: Firecrawl, Hyperbrowser for resilience
- **Configurable**: 40+ cities supported via config.json

## Quick Start

### Prerequisites
- Docker and Docker Compose
- PostgreSQL 15 (or use Docker)
- Python 3.11+
- Node.js 20+

### 1. Clone and Setup

```bash
cd /home/workspace/inyAcity

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - DATABASE_URL
# - SMTP credentials or SendGrid API key
# - Optional: Fallback scraper APIs
```

### 2. Start with Docker Compose

```bash
# Start all services (database, backend, frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Manual Setup (Development)

#### Database Setup

```bash
# Using Docker PostgreSQL
docker run -d \
  --name nocturne_db \
  -p 5432:5432 \
  -e POSTGRES_USER=nocturne \
  -e POSTGRES_PASSWORD=nocturne \
  -e POSTGRES_DB=nocturne \
  postgres:15-alpine

# Initialize database schema
cd backend
python3 -c "from database import init_db; init_db()"
```

#### Backend Setup

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd fronto

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

### 4. Initial Data Load

```bash
# Scrape events for a single city
cd backend
python3 scraper_integration.py ca--los-angeles

# Scrape all cities (takes time)
python3 scraper_integration.py
```

## API Endpoints

### Health & Info
- `GET /health` - API health status and stats

### Cities
- `GET /cities` - List all supported cities

### Events
- `GET /events/{city_id}` - Get events for a city
  - Query params: `start_date`, `end_date`, `limit`

### Scraping
- `POST /scrape/{city_id}` - Trigger scraping for a city
- `POST /scrape/all` - Scrape all cities

### Subscriptions
- `POST /subscribe` - Subscribe to email updates
  - Body: `{ "email": "...", "city_id": "..." }`
- `GET /subscriptions` - Get all subscriptions
- `DELETE /subscribe/{id}` - Unsubscribe

## Scheduled Tasks

### Daily Scraping (Recommended)

Set up a cron job to run daily:

```bash
# Edit crontab
crontab -e

# Add daily scraping at 2 AM
0 2 * * * cd /home/workspace/inyAcity && python3 cron_scraper.py daily

# Log location: logs/scraping_log.txt
```

### Manual Task Execution

```bash
# Full daily scrape
python3 cron_scraper.py daily

# Cleanup old events only
python3 cron_scraper.py cleanup

# Send test weekly digest
python3 cron_scraper.py digest
```

## Frontend Development

### Directory Structure
```
fronto/
├── components/
│   ├── CitySelector.tsx     - City selection page
│   ├── EventCard.tsx        - Individual event display
│   ├── SubscribeForm.tsx    - Email subscription
│   └── VibeChart.tsx       - Weekly activity chart
├── services/
│   └── apiService.ts        - API client functions
├── constants.ts             - City mappings, config
├── types.ts                - TypeScript interfaces
└── App.tsx                 - Main app component
```

### Adding New Cities

1. Add to `backend/scraper/config.json` in `SUPPORTED_LOCATIONS`
2. Add mapping to `backend/scraper_integration.py` in `CITY_MAPPING`
3. Add to `fronto/constants.ts` in `CITY_MAPPING`
4. Restart backend to load new city

## Database Schema

### Events Table
```sql
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  link VARCHAR(1000) UNIQUE NOT NULL,
  date DATE NOT NULL,
  time VARCHAR(100),
  location VARCHAR(500),
  description TEXT,
  source VARCHAR(50),
  city_id VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_events_city_date ON events(city_id, date);
CREATE INDEX idx_events_link ON events(link);
```

### Subscriptions Table
```sql
CREATE TABLE subscriptions (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  city_id VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  unsubscribed_at TIMESTAMP,
  UNIQUE(email, city_id)
);
```

## Email Configuration

### Option 1: SMTP (Gmail, etc.)

```bash
# .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@nocturne.events
```

### Option 2: SendGrid API

```bash
# .env
SENDGRID_API_KEY=SG.your-api-key
SENDGRID_FROM_EMAIL=noreply@nocturne.events
```

## Security Considerations

1. **Email Validation**: Backend validates email format via Pydantic
2. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
3. **Rate Limiting**: Add `slowapi` for production rate limiting
4. **CORS**: Configure CORS for production origins only
5. **Environment Variables**: Never commit `.env` file
6. **Database**: Use strong passwords in production

## Troubleshooting

### Backend Won't Start

```bash
# Check database connection
docker exec -it nocturne_db psql -U nocturne -c "SELECT 1"

# Check if port 8000 is available
lsof -i :8000

# Check logs
docker-compose logs backend
```

### Frontend Can't Connect to Backend

```bash
# Check VITE_API_URL in .env
# Should be: VITE_API_URL=http://localhost:8000

# Check if backend is running
curl http://localhost:8000/health
```

### Scraper Issues

```bash
# Check Playwright browsers
python3 -m playwright install --with-deps chromium

# Test single city scrape
cd backend
python3 scraper_integration.py ca--los-angeles

# Check logs
cat logs/scraping_log.txt
```

### Database Issues

```bash
# Reset database (WARNING: Deletes all data)
cd backend
python3 -c "from database import drop_all_tables, init_db; drop_all_tables(); init_db()"
```

## Performance Optimization

1. **Database Indexes**: Already created for city_id, date, link
2. **Async Operations**: All database queries use async SQLAlchemy
3. **Connection Pooling**: SQLAlchemy pool size = 10, max overflow = 20
4. **Caching**: Add Redis for API response caching (production)
5. **Pagination**: API endpoints support `limit` parameter

## Deployment Checklist

- [ ] Set strong database passwords
- [ ] Configure production CORS origins
- [ ] Set up SSL/HTTPS
- [ ] Configure email service (SMTP or SendGrid)
- [ ] Set up daily cron job for scraping
- [ ] Enable application logging
- [ ] Set up monitoring (Loki/Prometheus)
- [ ] Configure backup strategy for database
- [ ] Add rate limiting to API
- [ ] Build frontend for production (`npm run build`)

## License

This project integrates various open-source components. See individual licenses.

## Support

For issues or questions, check the implementation plans:
- `IMPLEMENTATION_PLAN.md` - High-level overview
- `TECHNICAL_IMPLEMENTATION_PLAN.md` - Detailed architecture
- `IMPLEMENTATION_TASKS_TIMELINE.md` - Development phases
- `POTENTIAL_CHALLENGES_SOLUTIONS.md` - Risk mitigation
