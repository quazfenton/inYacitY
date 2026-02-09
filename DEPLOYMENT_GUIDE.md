# Deployment Guide - Database Sync System

## Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Supabase database tables created
- [ ] API endpoints tested locally
- [ ] test_db_sync.py passes all tests
- [ ] Configuration matches deployment requirements
- [ ] Database backups configured
- [ ] Monitoring setup ready
- [ ] Error alerting configured

---

## Phase 1: Environment Setup (Day 1)

### 1.1 Prepare Supabase

```bash
# Login to Supabase console
# https://supabase.com/dashboard

# Create events table
CREATE TABLE events (
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
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_date ON events(date);
CREATE INDEX idx_location ON events(location);
CREATE INDEX idx_category ON events(category);
CREATE INDEX idx_price_tier ON events(price_tier);
CREATE INDEX idx_event_hash ON events(event_hash);
CREATE INDEX idx_scraped_at ON events(scraped_at);

# Create email_subscriptions table
CREATE TABLE email_subscriptions (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  city VARCHAR(50) NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (email, city)
);

CREATE INDEX idx_email ON email_subscriptions(email);
CREATE INDEX idx_city ON email_subscriptions(city);
CREATE INDEX idx_is_active ON email_subscriptions(is_active);
```

**Verify:**
```bash
# Test connection
curl -H "Authorization: Bearer <API_KEY>" \
  https://your-project.supabase.co/rest/v1/events?limit=0

# Should return: 200 OK, empty results
```

### 1.2 Environment Variables

**Create .env file:**

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here

# Flask (if applicable)
FLASK_ENV=production
FLASK_APP=backend/app.py
```

**Export for testing:**

```bash
source .env
echo "SUPABASE_URL: $SUPABASE_URL"
echo "SUPABASE_KEY: $SUPABASE_KEY"
```

### 1.3 Copy Files

```bash
# Core files
cp scraper/db_sync_enhanced.py scraper/db_sync.py
cp scraper/run_updated.py scraper/run.py
cp scraper/config_sync.json scraper/config.json  # or merge manually

# Verify files exist
ls -la scraper/db_sync.py
ls -la scraper/run.py
ls -la backend/api/scraper_api.py
```

---

## Phase 2: Local Testing (Day 2)

### 2.1 Run Validation Tests

```bash
cd scraper/
python test_db_sync.py
```

**Expected output:**
```
======================================================================
RUNNING DATABASE SYNC VALIDATION TESTS
======================================================================

[1] Configuration Loading
  ✓ PASS: Config loads without error
  ✓ PASS: DATABASE.SYNC_MODE exists
  ✓ PASS: Location loads

[2] Event Validation
  ✓ PASS: Valid event passes validation
  ...

======================================================================
TEST SUMMARY
======================================================================
Total Tests: 30
Passed: 30
Failed: 0
Success Rate: 100.0%
======================================================================
```

### 2.2 Test Supabase Connection

```bash
# Python script to test connection
python3 << 'EOF'
import os
from supabase import create_client

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

client = create_client(url, key)
response = client.table('events').select('*').limit(1).execute()
print(f"✓ Connected! Found {len(response.data)} events")
EOF
```

### 2.3 Test API Endpoints

```bash
# Start Flask server
python backend/app.py

# In another terminal:

# Health check
curl http://localhost:5000/api/scraper/health
# Expected: {"status": "healthy", "supabase_configured": true, ...}

# Sync status
curl http://localhost:5000/api/scraper/sync-status
# Expected: {"configured": true, "dedup_stats": {...}, ...}

# Test email subscription
curl -X POST http://localhost:5000/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","city":"ca--los-angeles"}'
# Expected: {"success": true, "message": "...", ...}
```

### 2.4 Test Scraper Runner

```bash
# Run with SYNC_MODE = 0 (disabled) first
cd scraper/
python run.py

# Check outputs
ls -la all_events.json
ls -la event_tracker.json
cat scraper_run_counter.txt
```

### 2.5 Test Sync Manually

```bash
# Set SYNC_MODE to 5 (always sync)
# Update config.json:
# "DATABASE": {"SYNC_MODE": 5}

# Run again
python run.py

# Check Supabase
# SELECT COUNT(*) FROM events;
# Should see events from scraper
```

---

## Phase 3: Staging Deployment (Day 3-4)

### 3.1 Deploy to Staging

```bash
# Build Docker image
docker build -t event-scraper:latest .

# Push to registry
docker push your-registry/event-scraper:latest

# Deploy to staging
kubectl apply -f k8s/staging/deployment.yaml
```

### 3.2 Staging Tests

```bash
# Test staging endpoints
curl https://staging.your-api.com/api/scraper/health

# Trigger test sync
curl -X POST https://staging.your-api.com/api/scraper/sync

# Monitor sync result
curl https://staging.your-api.com/api/scraper/sync-status

# Check database
# psql -h staging-db.supabase.co -U postgres -d postgres
# SELECT COUNT(*) FROM events;
```

### 3.3 Load Testing (Optional)

```bash
# Test email subscriptions under load
ab -n 100 -c 10 \
  -p data.json \
  -H "Content-Type: application/json" \
  https://staging.your-api.com/api/scraper/email-subscribe

# Monitor performance
# Should handle 100 requests in ~5-10 seconds
```

### 3.4 Monitoring Setup

```bash
# Setup error alerting
# Configure log aggregation (e.g., DataDog, NewRelic)

# Setup database monitoring
# - Monitor events table size
# - Monitor email_subscriptions growth
# - Monitor query performance

# Setup API monitoring
# - Response times
# - Error rates
# - Endpoint usage
```

---

## Phase 4: Production Deployment (Day 5)

### 4.1 Production Database

```bash
# Create backup of staging
pg_dump -h staging-db.supabase.co ... > backup-staging.sql

# Setup production database
# Execute same SQL schema in production

# Verify tables exist
curl -H "Authorization: Bearer <PROD_KEY>" \
  https://prod.supabase.co/rest/v1/events?limit=0
```

### 4.2 Production Secrets

```bash
# Set production environment variables
# Use your deployment platform's secret management:
# - AWS Secrets Manager
# - Kubernetes Secrets
# - Heroku Config Vars
# - etc.

# Variables to set:
SUPABASE_URL=https://prod.supabase.co
SUPABASE_KEY=prod_anon_key
FLASK_ENV=production
LOG_LEVEL=INFO
```

### 4.3 Production Deployment

```bash
# Deploy to production
docker push your-registry/event-scraper:prod-tag
kubectl apply -f k8s/production/deployment.yaml

# Verify deployment
kubectl get pods -n production
kubectl logs -f deployment/event-scraper

# Test production endpoints
curl https://api.your-domain.com/api/scraper/health
```

### 4.4 Production Testing

```bash
# Full integration test
curl -X POST https://api.your-domain.com/api/scraper/sync

# Monitor sync
sleep 5
curl https://api.your-domain.com/api/scraper/sync-status

# Check database
SELECT COUNT(*) FROM events;

# Test email subscription
curl -X POST https://api.your-domain.com/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"prod-test@example.com","city":"ca--los-angeles"}'
```

### 4.5 N8N Setup

```bash
# Setup N8N workflow for automated syncing

# Daily cron trigger (00:00 UTC)
├─ Load city rotation config
├─ Execute: curl -X POST http://scraper-service/scraper/run.py
├─ Wait 30 seconds
├─ Trigger: POST /api/scraper/sync if needed
├─ Send Slack notification with results

# Weekly cleanup
├─ Run: cleanup_old_events.sql
├─ Verify database size
└─ Alert if unexpected growth
```

---

## Phase 5: Post-Deployment (Ongoing)

### 5.1 Monitoring Dashboard

```
Key Metrics to Track:

Events Table:
├─ Total events: SELECT COUNT(*) FROM events
├─ Events by category: GROUP BY category
├─ Events by price tier: GROUP BY price_tier
├─ Average events per day
└─ Growth rate

Email Subscriptions:
├─ Total subscribers: COUNT(DISTINCT email)
├─ Active subscriptions: WHERE is_active = true
├─ Subscribers by city: GROUP BY city
└─ Subscription growth rate

Sync Performance:
├─ Sync duration: (end_time - start_time)
├─ Events synced per run
├─ Duplicates removed
├─ Errors per sync
└─ API response times

System Health:
├─ Database connection pool
├─ Disk usage
├─ Memory usage
├─ CPU usage
└─ Error rates
```

### 5.2 Monitoring Queries

```sql
-- Events synced today
SELECT COUNT(*) 
FROM events 
WHERE DATE(created_at) = CURRENT_DATE;

-- Events by source
SELECT source, COUNT(*) 
FROM events 
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY source;

-- Subscription stats
SELECT city, COUNT(*) 
FROM email_subscriptions 
WHERE is_active = true
GROUP BY city;

-- Database size
SELECT 
  pg_size_pretty(pg_total_relation_size('events')) as events_size,
  pg_size_pretty(pg_total_relation_size('email_subscriptions')) as subs_size;

-- Slowest queries
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

### 5.3 Alerting Rules

```
Alert Thresholds:

Critical:
├─ API health check fails: Immediate
├─ Database connection fails: Immediate
├─ Sync error rate > 10%: Immediate
└─ Disk space < 10%: Immediate

Warning:
├─ API response time > 5s: 5min sustained
├─ Sync error rate > 1%: 15min sustained
├─ Database queries > 2s: 10min sustained
└─ Memory usage > 80%: 10min sustained

Info (for monitoring):
├─ Sync completed
├─ New events synced
├─ Subscription activity
└─ Scheduled maintenance
```

### 5.4 Maintenance Tasks

```
Daily:
├─ Check error logs
├─ Monitor sync status
├─ Verify email subscriptions

Weekly:
├─ Review performance metrics
├─ Check database growth
├─ Run cleanup queries
├─ Test email notifications

Monthly:
├─ Archive old logs
├─ Optimize database indexes
├─ Review and update documentation
├─ Plan capacity improvements

Quarterly:
├─ Full disaster recovery test
├─ Security audit
├─ Performance optimization
└─ Plan upgrades
```

---

## Troubleshooting Guide

### Issue: "Supabase not configured"

```bash
# Check env vars
echo $SUPABASE_URL
echo $SUPABASE_KEY

# If empty, set them
export SUPABASE_URL="https://..."
export SUPABASE_KEY="..."

# Test connection
python3 -c "
from supabase import create_client
import os
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
print('✓ Connected!')
"
```

### Issue: "No events syncing"

```bash
# Check sync config
grep "SYNC_MODE" scraper/config.json

# Check run counter
cat scraper/scraper_run_counter.txt

# Check all_events.json exists and has content
cat scraper/all_events.json | head -20

# Run sync manually
curl -X POST http://localhost:5000/api/scraper/sync -v
```

### Issue: "Duplicate events appearing"

```bash
# Check UNIQUE constraint
SELECT * FROM information_schema.table_constraints
WHERE table_name = 'events' AND constraint_type = 'UNIQUE';

# Rebuild event tracker
rm scraper/event_tracker.json  # Start fresh

# Verify event hashes are unique
SELECT event_hash, COUNT(*) 
FROM events 
GROUP BY event_hash 
HAVING COUNT(*) > 1;
```

### Issue: "API endpoints return 404"

```bash
# Check blueprint registration
grep -r "register_blueprint" backend/

# Should include:
# app.register_blueprint(scraper_api)

# Verify imports
grep "from backend.api.scraper_api" backend/app.py

# Test directly
curl -v http://localhost:5000/api/scraper/health
```

---

## Rollback Procedure

If something goes wrong:

```bash
# 1. Stop current deployment
kubectl rollout undo deployment/event-scraper

# 2. Restore database backup
psql -h db-host -U user < backup-latest.sql

# 3. Clear cache
rm scraper/scraper_run_counter.txt
rm scraper/event_tracker.json

# 4. Investigate issue
# - Check logs
# - Review error messages
# - Verify configuration

# 5. Fix and redeploy
# - Apply fixes
# - Run tests
# - Deploy again
```

---

## Success Criteria

✅ **Phase 1 Complete**
- Supabase tables created
- Environment variables set
- Files copied to correct locations

✅ **Phase 2 Complete**
- All tests passing (30/30)
- API endpoints responding
- Local sync working

✅ **Phase 3 Complete**
- Staging deployment stable
- Email subscriptions working
- Monitoring configured

✅ **Phase 4 Complete**
- Production deployment successful
- All endpoints working
- Database populated with events

✅ **Phase 5 Complete**
- N8N automation running
- Daily syncs successful
- Monitoring active
- Alerts configured

---

## Quick Reference

```bash
# View current status
curl http://your-api/api/scraper/health

# Trigger sync
curl -X POST http://your-api/api/scraper/sync

# Check sync status
curl http://your-api/api/scraper/sync-status

# Subscribe email
curl -X POST http://your-api/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","city":"ca--los-angeles"}'

# View tracker stats
cat scraper/event_tracker.json

# View run counter
cat scraper/scraper_run_counter.txt

# Check database
psql -h your-db-host -U postgres -d postgres \
  -c "SELECT COUNT(*) FROM events;"
```

---

## Support Contact

For deployment issues:
1. Check troubleshooting guide above
2. Review logs: `kubectl logs deployment/event-scraper`
3. Check documentation: DB_SYNC_INTEGRATION_GUIDE.md
4. Run tests: `python scraper/test_db_sync.py`

---

**Ready to Deploy** ✅
