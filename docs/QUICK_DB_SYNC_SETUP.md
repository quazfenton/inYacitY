# Quick Database Sync Setup

## TL;DR - 5 minute setup

### 1. Copy files

```bash
cp scraper/db_sync_enhanced.py scraper/db_sync.py
cp scraper/run_updated.py scraper/run.py
cp scraper/config_sync.json scraper/config.json  # or merge manually
```

### 2. Set environment variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your_anon_key"
```

### 3. Create database tables

In Supabase SQL editor, run:

```sql
-- Events table
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
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_date ON events(date);
CREATE INDEX idx_location ON events(location);
CREATE INDEX idx_category ON events(category);
CREATE INDEX idx_price_tier ON events(price_tier);
CREATE INDEX idx_event_hash ON events(event_hash);

-- Email subscriptions table
CREATE TABLE IF NOT EXISTS email_subscriptions (
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

### 4. Update config.json

Add this to config.json:

```json
{
  "DATABASE": {
    "SYNC_MODE": 5,
    "COMMENTS": "0=disabled | 1-4=every Nth run | 5+=every run"
  }
}
```

**SYNC_MODE values:**
- `0` = Disabled
- `1-4` = Sync every Nth run (1=every, 2=every 2nd, 3=every 3rd, etc.)
- `5+` = Sync every run

### 5. Register API endpoints

In your Flask app (`backend/api/__init__.py` or main app file):

```python
from backend.api.scraper_api import scraper_api

app.register_blueprint(scraper_api)
```

### 6. Test

```bash
# Test health
curl http://localhost:5000/api/scraper/health

# Test sync
curl -X POST http://localhost:5000/api/scraper/sync

# Test email subscription
curl -X POST http://localhost:5000/api/scraper/email-subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","city":"ca--los-angeles"}'
```

### Done! 🎉

Run your scrapers and they'll automatically sync to Supabase based on SYNC_MODE.

---

## Configuration Examples

### Real-time (every run)
```json
{"DATABASE": {"SYNC_MODE": 5}}
```
**Use:** Frontend needs live data, not concerned about API calls

### Batch every 5 runs (e.g., 5 cities)
```json
{"DATABASE": {"SYNC_MODE": 5}}
```
Then update config daily:
```json
{"DATABASE": {"SYNC_MODE": 0}}  // Set to 0 after sync complete
```

### Batch every 3 runs
```json
{"DATABASE": {"SYNC_MODE": 3}}
```
Day 1: LA run (1) → no sync
Day 2: NY run (2) → no sync
Day 3: DC run (3) → SYNC ✓
Day 4: Miami run (4) → no sync
...

### Disabled (manual only)
```json
{"DATABASE": {"SYNC_MODE": 0}}
```
Then call API manually:
```bash
curl -X POST http://localhost:5000/api/scraper/sync
```

---

## API Endpoints Reference

### Email Subscriptions

```bash
# Subscribe
POST /api/scraper/email-subscribe
{"email": "user@example.com", "city": "ca--los-angeles"}

# Unsubscribe from city
POST /api/scraper/email-unsubscribe
{"email": "user@example.com", "city": "ca--los-angeles"}

# Unsubscribe from all
POST /api/scraper/email-unsubscribe
{"email": "user@example.com"}
```

### Database Sync

```bash
# Trigger sync
POST /api/scraper/sync
{}

# Get sync status
GET /api/scraper/sync-status

# Health check
GET /api/scraper/health
```

---

## What Changed?

### New Files
- `db_sync_enhanced.py` - Enhanced sync with email, 2D tagging, better validation
- `scraper_api.py` - Flask API endpoints
- `run_updated.py` - run.py with sync integration
- `config_sync.json` - Config with DATABASE.SYNC_MODE

### Enhanced Features
- ✅ Automatic price tier calculation (Free, <$20, <$50, etc.)
- ✅ Automatic category tagging (Concert, Tech, Nightlife, etc.)
- ✅ Email subscriptions grouped by city
- ✅ API endpoints for frontend integration
- ✅ Configurable sync batching
- ✅ Event deduplication tracking
- ✅ Automatic cleanup of past events

---

## File Locations

```
project/
├── scraper/
│   ├── run.py (updated)
│   ├── db_sync.py (enhanced)
│   ├── config.json (with DATABASE.SYNC_MODE)
│   └── event_tracker.json (auto-created)
├── backend/api/
│   └── scraper_api.py (new)
└── DB_SYNC_INTEGRATION_GUIDE.md (complete reference)
```

---

## Environment Variables

```bash
# Required for Supabase sync
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
```

Set in `.env` file or export before running:
```bash
source .env
python scraper/run.py
```

---

## Monitoring

Check what's happening:

```bash
# See dedup tracker
cat scraper/event_tracker.json

# See run counter
cat scraper/scraper_run_counter.txt

# Check all events synced
curl http://localhost:5000/api/scraper/sync-status
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Supabase not configured" | Check SUPABASE_URL and SUPABASE_KEY env vars |
| Endpoint returns 404 | Make sure scraper_api blueprint is registered |
| Email subscription fails | Verify email format is valid |
| No events syncing | Check SYNC_MODE config and run counter |
| Duplicate events appearing | Rebuild event_hash in tracker, check UNIQUE constraints |

---

## Next: Frontend Integration

Create a subscription form component:

```typescript
import { useEventSubscription } from '@/hooks/useEventSubscription';

export function EmailSubscriptionForm() {
  const { subscribe, isLoading } = useEventSubscription();
  const [email, setEmail] = useState('');
  const city = useUserCity(); // from geolocation

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await subscribe(email, city);
      // Show success
    } catch {
      // Show error
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter email"
        required
      />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Subscribing...' : 'Subscribe to Events'}
      </button>
    </form>
  );
}
```

---

For detailed docs, see: `DB_SYNC_INTEGRATION_GUIDE.md`
