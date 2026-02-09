# n8n Daily Scraper - Quick Start (10 minutes)

## TL;DR

1. Install n8n: `docker-compose up -d`
2. Import workflow: `nocturne-daily-scraper.json`
3. Set environment variables
4. Click "Activate"
5. Done! Runs daily at midnight UTC

## Step 1: Start n8n (2 minutes)

### Docker (Recommended)

```bash
# Create directory
mkdir nocturne-automation
cd nocturne-automation

# Copy this docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_ENCRYPTION_KEY=nocturne-automation-key-32-chars-here
      - NOCTURNE_API_URL=http://your-backend-ip:8000
      - SUPABASE_URL=https://your-project.supabase.co
      - SUPABASE_KEY=your-key-here
      - SLACK_WEBHOOK_URL=https://hooks.slack.com/...
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped

volumes:
  n8n_data:
EOF

# Start it
docker-compose up -d

# Wait 30 seconds for startup
sleep 30

# Access at http://localhost:5678
```

### Without Docker

```bash
# Install Node.js 18+
# Then npm install -g n8n
# Then n8n start
# Access at http://localhost:5678
```

## Step 2: Import Workflow (3 minutes)

1. Open http://localhost:5678
2. Create account and sign in
3. Click "+" to create new workflow
4. Click "Import from file"
5. Select `nocturne-daily-scraper.json`
6. Click "Import"

## Step 3: Configure (3 minutes)

### Set Environment Variables

**In docker-compose.yml**, update:
```yaml
environment:
  - NOCTURNE_API_URL=http://your-backend-ip:8000
  - SUPABASE_URL=https://your-project.supabase.co
  - SUPABASE_KEY=your-anon-key
  - SLACK_WEBHOOK_URL=https://hooks.slack.com/... (optional)
```

Then restart:
```bash
docker-compose restart n8n
```

### Or Set in n8n UI

1. Go to Settings (gear icon)
2. Environment Variables
3. Add each variable
4. Save

## Step 4: Test (1 minute)

1. Open workflow
2. Click "Execute Workflow" (play button)
3. Watch nodes run
4. Should complete in ~50 seconds

Check outputs:
- ✅ Trigger → timestamp
- ✅ Variables → city name
- ✅ Scraper → 200 OK
- ✅ Events → array of events
- ✅ Supabase → success
- ✅ Slack → notification

## Step 5: Activate (30 seconds)

1. Click "Activate" toggle (top right)
2. Workflow now runs daily at midnight UTC
3. Done! 🎉

## What Happens Daily

```
00:00 UTC → Workflow starts
  → Picks rotating city (LA on day 1, NYC on day 2, etc)
  → Calls /scrape/{city_id}
  → Waits 45 seconds
  → Fetches events
  → Syncs to Supabase
  → Syncs to Notion (optional)
  → Sends Slack notification
  → Done!
```

## Check If It's Working

### Day 1 (after activation)
- Midnight UTC workflow runs
- Check Slack for notification
- Check Supabase table for events

### Next Day
- Runs again at midnight with different city
- Repeat

## Customize Rotation

To change which cities run:

1. Click workflow
2. Click "Set Variables" node
3. Edit "cities" array
4. Save

Example - rotate every 3 days instead of 20:
```javascript
const cities = [
  "ca--los-angeles",
  "ny--new-york",
  "ca--san-francisco"
];
```

## Troubleshooting

### Workflow not running at midnight
- Check workflow is activated (toggle is ON)
- Check n8n container is running: `docker ps`
- Check system clock is correct

### Events not syncing to Supabase
- Check SUPABASE_URL and SUPABASE_KEY are correct
- Verify Supabase tables exist
- Run workflow manually and check errors

### Slack notification not arriving
- Check SLACK_WEBHOOK_URL is correct
- Verify Slack app is authorized to channel
- Check n8n logs for errors

## Environment Variables Reference

| Variable | Example | Required |
|----------|---------|----------|
| NOCTURNE_API_URL | `http://localhost:8000` | ✅ Yes |
| SUPABASE_URL | `https://project.supabase.co` | ✅ Yes (for Supabase) |
| SUPABASE_KEY | `eyJhbGc...` | ✅ Yes (for Supabase) |
| SLACK_WEBHOOK_URL | `https://hooks.slack.com/...` | ❌ Optional |
| NOTION_DATABASE_ID | `123abc...` | ❌ Optional |
| NOTION_API_KEY | `secret_xyz...` | ❌ Optional |

## Default Schedule

**When**: Daily at 00:00 (midnight) UTC

To change:
1. Click "Daily Trigger" node
2. Edit "Trigger at Hour" (0-23)
3. Edit "Trigger at Minute" (0-59)

Example: Run at 6 AM UTC
- Hour: `6`
- Minute: `0`

## Default Cities (20)

```
Day 1: Los Angeles     Day 11: Atlanta
Day 2: New York        Day 12: Portland
Day 3: San Francisco   Day 13: Phoenix
Day 4: Chicago         Day 14: Houston
Day 5: Austin          Day 15: Las Vegas
Day 6: Miami           Day 16: Detroit
Day 7: Washington DC   Day 17: Charlotte
Day 8: Denver          Day 18: Nashville
Day 9: Dallas          Day 19: Philadelphia
Day 10: Seattle        Day 20: Boston → Repeats

(Then Boston → LA again)
```

## Monitoring

Check executions daily:

```bash
# View workflow executions in UI
# Workflow → "Executions" tab

# Or check Docker logs
docker logs nocturne-automation_n8n_1 | grep -i "workflow"
```

## Next Steps

### For More Control
- Read `N8N_SETUP.md` for detailed configuration
- Add conditional logic (skip cities with no events)
- Add error handling and retries

### For Custom Scheduling
- Multiple workflows for different times
- Conditional execution based on day/week
- Manual triggers for testing

### For Monitoring
- Set up Slack alerts for failures
- Log to database for analytics
- Export execution history

## Support

- **n8n Docs**: https://docs.n8n.io/
- **Nocturne Docs**: See N8N_SETUP.md
- **Supabase Issues**: Check SUPABASE_SETUP.md

---

**Setup Time**: ~10 minutes  
**Running Time**: ~50 seconds per city  
**Cost**: Free (self-hosted) or $20-40/month (cloud)
