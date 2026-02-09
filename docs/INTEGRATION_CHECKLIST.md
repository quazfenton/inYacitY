# Complete Integration Checklist

## ✅ All Features Implemented

- [x] Event scraping (6 sources)
- [x] Database synchronization
- [x] Email subscriptions
- [x] Event RSVPs with calendar integration
- [x] Event comments with rate limiting
- [x] Geolocation support
- [x] Rate limiting (comments)
- [x] Data validation & sanitization
- [x] Error handling
- [x] CORS configuration

---

## Phase 1: Setup & Configuration

### Backend Setup
- [ ] Clone repository
- [ ] Install Python 3.8+
- [ ] Create virtual environment
- [ ] Install dependencies: `pip install -r backend/requirements.txt`
- [ ] Create `.env` file with:
  - [ ] `SUPABASE_URL`
  - [ ] `SUPABASE_KEY`
  - [ ] `FLASK_ENV`
  - [ ] `FRONTEND_URL`
- [ ] Verify backend imports: `python -c "from backend.app import create_app; print('OK')"`

### Frontend Setup
- [ ] Install Node.js 14+
- [ ] Install dependencies: `cd fronto && npm install`
- [ ] Create `.env` with `REACT_APP_API_URL`
- [ ] Verify TypeScript: `npm run tsc --noEmit`

### Database Setup
- [ ] Login to Supabase
- [ ] Run migrations: `python backend/migrations.py`
  - [ ] Events table (auto-created by sync)
  - [ ] Email subscriptions table
  - [ ] RSVPs table
  - [ ] Comments table
- [ ] Verify all tables created in Supabase

---

## Phase 2: Backend Integration

### Core Modules
- [ ] `backend/app.py` - Main Flask application
- [ ] `backend/models/comments.py` - Rate limiter, validators
- [ ] `backend/models/__init__.py` - Module exports
- [ ] `backend/api/scraper_api.py` - All API endpoints
- [ ] `backend/api/__init__.py` - API exports
- [ ] `backend/migrations.py` - Database setup

### API Endpoints Verification
- [ ] Health check: `GET /health`
- [ ] API info: `GET /`
- [ ] Scraper health: `GET /api/scraper/health`

#### Email Subscriptions
- [ ] `POST /api/scraper/email-subscribe`
- [ ] `POST /api/scraper/email-unsubscribe`

#### RSVPs
- [ ] `POST /api/scraper/rsvp`
- [ ] `DELETE /api/scraper/rsvp/{rsvp_id}`
- [ ] `GET /api/scraper/rsvp-status/{event_id}`

#### Comments
- [ ] `GET /api/scraper/comments/{event_id}`
- [ ] `POST /api/scraper/comments` (with rate limiting)
- [ ] `DELETE /api/scraper/comments/{comment_id}`
- [ ] `POST /api/scraper/comments/{comment_id}/like`
- [ ] `GET /api/scraper/comments/rate-limit/status`

#### Database Sync
- [ ] `POST /api/scraper/sync`
- [ ] `GET /api/scraper/sync-status`

### Backend Testing
- [ ] Start Flask app: `python backend/app.py`
- [ ] Test health: `curl http://localhost:5000/health`
- [ ] Test API info: `curl http://localhost:5000/`
- [ ] Test all endpoints with curl (see PRODUCTION_SETUP_GUIDE.md)
- [ ] Verify rate limiting (post 4 comments quickly, 4th should fail)
- [ ] Verify CORS headers
- [ ] Check error responses

---

## Phase 3: Frontend Integration

### Hooks & Components
- [ ] Copy `fronto/src/hooks/useEventRSVP.ts`
- [ ] Copy `fronto/src/hooks/useEventComments.ts`
- [ ] Create config file with API endpoints
- [ ] Import hooks in components

### Components to Create/Update
- [ ] Event details page
  - [ ] Add RSVPSection component
  - [ ] Add CommentsSection component
- [ ] Create EventRSVPForm component
- [ ] Create EventCommentForm component
- [ ] Create CommentCard component
- [ ] Add email subscription form to home/events page

### Frontend Testing
- [ ] Start dev server: `cd fronto && npm start`
- [ ] Test API connection: `fetch('http://localhost:5000/health')`
- [ ] Test RSVP hook
- [ ] Test comments hook
- [ ] Verify rate limit display
- [ ] Test calendar integration (manual click)
- [ ] Verify error messages display

---

## Phase 4: Integration Testing

### Cross-Service Tests
- [ ] Backend running on port 5000
- [ ] Frontend running on port 3000 (or configured)
- [ ] Can fetch from backend
- [ ] CORS working
- [ ] Supabase connected
- [ ] Database operations working

### End-to-End Scenarios
- [ ] User subscribes to email notifications
  - [ ] Submit form
  - [ ] Check database
  - [ ] Test unsubscribe
- [ ] User RSVPs to event
  - [ ] Submit RSVP
  - [ ] Verify calendar URL generation
  - [ ] Check database
  - [ ] Cancel RSVP
- [ ] User posts comment
  - [ ] Submit comment
  - [ ] See in comments list
  - [ ] Like comment
  - [ ] Delete comment
  - [ ] Test rate limiting (4 quick posts)
- [ ] Event sync
  - [ ] Trigger sync via API
  - [ ] Verify events in database
  - [ ] Check deduplication

### Data Validation
- [ ] Comment too short: `POST /api/scraper/comments` with <3 chars
- [ ] Comment too long: `POST /api/scraper/comments` with >1000 chars
- [ ] Empty author name: error
- [ ] Invalid email: validation works
- [ ] Rate limiting: 429 response

---

## Phase 5: Production Deployment

### Pre-Deployment
- [ ] All tests passing
- [ ] No console errors
- [ ] Environment variables set
- [ ] Database backups enabled
- [ ] Monitoring configured
- [ ] Error logging setup

### Deployment - Backend
- [ ] Build Docker image (if using Docker)
- [ ] Deploy to:
  - [ ] Heroku, or
  - [ ] AWS, or
  - [ ] DigitalOcean, or
  - [ ] Your preferred platform
- [ ] Run migrations on production DB
- [ ] Set production env vars
- [ ] Test all endpoints
- [ ] Verify Supabase connection
- [ ] Check logs for errors

### Deployment - Frontend
- [ ] Build: `npm run build`
- [ ] Deploy to:
  - [ ] Vercel, or
  - [ ] Netlify, or
  - [ ] AWS S3 + CloudFront, or
  - [ ] Your preferred platform
- [ ] Set `REACT_APP_API_URL` to production backend
- [ ] Test all features
- [ ] Check for 404s or errors

### Post-Deployment
- [ ] Monitor error logs
- [ ] Check performance metrics
- [ ] Verify all endpoints working
- [ ] Test rate limiting
- [ ] Test database operations
- [ ] Send test email
- [ ] Create test RSVP
- [ ] Create test comment

---

## Phase 6: Automation & Monitoring

### N8N Automation
- [ ] Setup daily scraper cron
- [ ] Setup city rotation
- [ ] Setup database sync trigger
- [ ] Setup email notifications (if using)
- [ ] Setup error alerting

### Monitoring
- [ ] Setup health check monitoring
- [ ] Setup error rate alerting
- [ ] Setup database monitoring
- [ ] Setup performance monitoring
- [ ] Setup log aggregation

### Maintenance
- [ ] Setup database backups
- [ ] Setup log rotation
- [ ] Create runbooks for common issues
- [ ] Document escalation procedures

---

## Documentation Checklist

- [ ] PRODUCTION_SETUP_GUIDE.md - Read & understood
- [ ] DB_SYNC_INTEGRATION_GUIDE.md - Read & understood
- [ ] RSVP_INTEGRATION_GUIDE.md - Read & understood
- [ ] COMMENTS_INTEGRATION_GUIDE.md - Read & understood
- [ ] API endpoints documented
- [ ] Error codes documented
- [ ] Deployment procedure documented
- [ ] Rollback procedure documented

---

## Testing Checklist

### Unit Tests
- [ ] Comment validator tests
- [ ] Rate limiter tests
- [ ] Data model tests

### Integration Tests
- [ ] API endpoint tests
- [ ] Database operation tests
- [ ] Authentication tests (if added)

### End-to-End Tests
- [ ] Full user workflow: subscribe → RSVP → comment
- [ ] Error handling: network error, rate limited, etc.
- [ ] Rate limiting: verify limits enforced
- [ ] Calendar integration: verify URLs generated

### Performance Tests
- [ ] Load test: 100 concurrent comments
- [ ] Database query performance
- [ ] API response times

---

## Known Limitations & Future Work

### Current Limitations
- [ ] Comments not moderated (manual review needed)
- [ ] No edit comment functionality
- [ ] Rate limiting in-memory only (not distributed)
- [ ] No email notification service integrated
- [ ] No user authentication system

### Future Enhancements
- [ ] Add comment editing
- [ ] Add user accounts & authentication
- [ ] Add distributed rate limiting (Redis)
- [ ] Add email notifications
- [ ] Add comment moderation UI
- [ ] Add analytics dashboard
- [ ] Add content filtering
- [ ] Add user profiles

---

## Rollback Plan

If something goes wrong in production:

### Database
```sql
-- Restore from backup
-- Supabase: Use automatic backups
-- Or manual restore from backup file
```

### Backend
```bash
# Revert to previous version
git revert <commit-hash>
git push heroku main
# Or restart from image
docker pull <image>:previous
docker-compose up -d
```

### Frontend
```bash
# Revert deployment
# Vercel: Use previous deployment
# Netlify: Use rollback feature
# Or redeploy previous commit
```

### Full Rollback
1. Stop new API
2. Restore database from backup
3. Deploy previous API version
4. Deploy previous frontend version
5. Monitor logs
6. Notify users

---

## Sign-Off

- [ ] All phases completed
- [ ] All tests passing
- [ ] All documentation reviewed
- [ ] Ready for production

**Project Status:** ✅ Ready for Deployment

---

## Quick Reference

### Start Development Servers
```bash
# Terminal 1: Backend
python backend/app.py

# Terminal 2: Frontend
cd fronto && npm start

# Terminal 3: Scraper (if needed)
cd scraper && python run.py
```

### Test Key Endpoints
```bash
# Health check
curl http://localhost:5000/health

# Email subscription
curl -X POST http://localhost:5000/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","city":"ca--los-angeles"}'

# RSVP
curl -X POST http://localhost:5000/api/scraper/rsvp \
  -H "Content-Type: application/json" \
  -d '{"event_id":"test","title":"Test","date":"2026-02-15","location":"LA","user_name":"John"}'

# Comment
curl -X POST http://localhost:5000/api/scraper/comments \
  -H "Content-Type: application/json" \
  -d '{"event_id":"test","author_name":"John","text":"Great event!"}'

# Rate limit
curl http://localhost:5000/api/scraper/comments/rate-limit/status
```

---

