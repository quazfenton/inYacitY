# n8n Workflow Setup - Nocturne Daily Scraper

## Overview

This n8n workflow automatically:
- Runs daily at a scheduled time (default: midnight UTC)
- Rotates through cities (20+ cities, one per day)
- Triggers the Nocturne backend scraper
- Waits for scraping to complete (45 seconds)
- Fetches the newly scraped events
- Syncs events to Supabase **and/or** Notion
- Sends Slack notification with summary

**Example**: Jan 1 = LA, Jan 2 = NYC, Jan 3 = SF, ... (repeating every 20 days)

## Prerequisites

✅ n8n instance running (self-hosted or cloud)  
✅ Nocturne backend API accessible  
✅ Supabase project configured (or Notion)  
✅ Docker (if self-hosting n8n)

## Step 1: Install n8n

### Option A: Self-Hosted with Docker

```bash
# Create docker-compose.yml
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
      - N8N_PROTOCOL=http
      - NODE_ENV=production
      - N8N_ENCRYPTION_KEY=your-secure-random-key-here-32-chars
      # Enable nodes
      - N8N_NODES_INCLUDE=n8n-nodes-base.httpRequest,n8n-nodes-base.cron,n8n-nodes-base.wait,n8n-nodes-base.set,n8n-nodes-base.code,@n8n/n8n-nodes-notion
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped

volumes:
  n8n_data:
EOF

# Start n8n
docker-compose up -d

# Access at http://localhost:5678
```

### Option B: Cloud (n8n.cloud)

1. Go to https://n8n.cloud
2. Sign up for free account
3. Creates managed n8n instance automatically

## Step 2: Configure Environment Variables

In n8n, you need to set these environment variables (or they can be passed at runtime):

### Required
```bash
NOCTURNE_API_URL=http://your-backend:8000
```

### For Supabase Sync
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_CREDENTIAL_TYPE=http
```

### For Notion Sync (Optional)
```bash
NOTION_DATABASE_ID=your-notion-database-id
NOTION_API_KEY=your-notion-integration-token
```

### For Slack Notifications (Optional)
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Set Environment Variables in n8n

**Docker Method**:
```bash
# Edit docker-compose.yml and add to environment:
environment:
  - NOCTURNE_API_URL=http://nocturne-backend:8000
  - SUPABASE_URL=https://your-project.supabase.co
  - SUPABASE_KEY=your-key
  - SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Restart
docker-compose down && docker-compose up -d
```

**n8n Cloud Method**:
1. Go to Settings → Environment Variables
2. Add each variable
3. Save

## Step 3: Import the Workflow

### Method 1: Import JSON File

1. Open n8n dashboard (http://localhost:5678)
2. Click "+" to create new workflow
3. Click "Import from file"
4. Select `nocturne-daily-scraper.json`
5. Click "Import"

### Method 2: Manual Copy-Paste

1. Create new workflow
2. Copy JSON from `nocturne-daily-scraper.json`
3. Menu → Import from clipboard
4. Paste JSON and import

### Method 3: API Upload

```bash
# Upload workflow via API
curl -X POST http://localhost:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @nocturne-daily-scraper.json
```

## Step 4: Configure Workflow Nodes

### 1. Daily Trigger Node

Currently set to run at **00:00 UTC** daily.

To change timing:
1. Click "Daily Trigger (Midnight UTC)" node
2. Set "Trigger at Hour" (0-23)
3. Set "Trigger at Minute" (0-59)

**Example**: To run at 3 AM UTC:
- Hour: `3`
- Minute: `0`

### 2. Set Variables Node

The cities list is hardcoded. To modify:

1. Click "Set Variables" node
2. Edit "cities" assignment
3. Replace with your desired cities

**Current cities** (20 total):
```
ca--los-angeles
ny--new-york
ca--san-francisco
il--chicago
tx--austin
fl--miami
dc--washington
co--denver
tx--dallas
wa--seattle
ma--boston
ga--atlanta
or--portland
az--phoenix
tx--houston
nv--las-vegas
mi--detroit
nc--charlotte
tn--nashville
pa--philadelphia
```

To add more:
```javascript
const cities = [
  "ca--los-angeles",
  "ny--new-york",
  // ... add more
  "ca--sacramento",
  "ca--san-jose"
];
```

### 3. Trigger Backend Scraper Node

Should work automatically if NOCTURNE_API_URL is set.

To test manually:
1. Click node
2. Click "Execute Node" (play button)
3. Check response

### 4. Wait for Scraper

Currently set to 45 seconds. Adjust if:
- Cities have many events: increase to 60s
- Cities have few events: decrease to 30s

Change by editing "Wait for Scraper" node.

### 5. Fetch Scraped Events

Fetches up to 500 events per city. To change:

1. Click node
2. Edit URL parameter: `?limit=500`
3. Change `500` to desired limit

### 6. Sync to Supabase

Should work automatically if SUPABASE_URL and SUPABASE_KEY are set.

**To test**:
1. Run workflow manually
2. Check Supabase Table Editor → events table
3. Should see new events

**Troubleshooting**:
- Check Supabase tables exist (see SUPABASE_SETUP.md)
- Verify API key is correct
- Check n8n logs for errors

### 7. Sync to Notion (Optional)

Only works if Notion integration is set up.

**To enable**:

1. In Notion, create integration:
   - Go to https://www.notion.com/my-integrations
   - Click "Create new integration"
   - Name: "Nocturne Events"
   - Copy "Internal Integration Token"
   - Set as NOTION_API_KEY

2. Create Notion database:
   - New page with database
   - Add properties:
     - Title (text)
     - Link (URL)
     - Date (date)
     - Time (text)
     - Location (text)
     - Description (text)
     - Source (select: eventbrite, meetup, luma)
     - City (text)

3. Get database ID:
   - Open database in Notion
   - URL: `https://notion.so/workspace/DATABASE_ID?v=...`
   - Copy DATABASE_ID
   - Set as NOTION_DATABASE_ID

4. In n8n workflow:
   - Click "Sync Events to Notion" node
   - Click "Authenticate" and paste integration token
   - Select database
   - Map fields (Title → Title, Link → Link, etc.)

### 8. Slack Notification (Optional)

To enable Slack notifications:

1. Create Slack App:
   - Go to https://api.slack.com/apps
   - Click "Create New App"
   - Choose "From scratch"
   - Name: "Nocturne"
   - Select workspace
   - Click "Create App"

2. Enable Incoming Webhooks:
   - In app settings, go to "Incoming Webhooks"
   - Click "Add New Webhook to Workspace"
   - Select channel (e.g., #automation)
   - Authorize
   - Copy webhook URL

3. Set environment variable:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX
   ```

4. In n8n workflow:
   - Node will automatically use this URL
   - No additional setup needed

## Step 5: Test the Workflow

### Quick Test

1. Open workflow in n8n
2. Click "Execute Workflow" (play button, top right)
3. Watch nodes execute
4. Check each node output:
   - Trigger → should show timestamp
   - Set Variables → should show city_to_scrape
   - Trigger Scraper → should return 200 OK
   - Fetch Events → should show events array
   - Transform → should show transformed events
   - Sync nodes → should show success

### Troubleshooting Errors

**"Can't resolve environment variable NOCTURNE_API_URL"**
- Set environment variable in n8n settings
- Or hard-code URL in HTTP node

**"404 Not Found" from scraper**
- Check NOCTURNE_API_URL is correct
- Verify backend is running
- Check city_id is valid

**"Events syncing fails"**
- Check Supabase credentials
- Verify tables exist in Supabase
- Check RLS policies allow inserts

**"Notion sync fails"**
- Check integration token is valid
- Verify database ID is correct
- Ensure database properties match

## Step 6: Activate Daily Schedule

When satisfied with testing:

1. Open workflow
2. Click "Activate" (toggle at top)
3. Workflow now runs daily at scheduled time

To deactivate:
- Click toggle again

## Step 7: Monitor Executions

### View Execution History

1. Open workflow
2. Click "Executions" tab
3. See all run history:
   - Timestamp
   - Status (Success/Error)
   - Duration
   - Data processed

### View Logs

1. Click workflow execution
2. See full execution details
3. Expand nodes to see inputs/outputs
4. Look for errors

### Set Alerts (Optional)

1. Go to Settings → Notifications
2. Create notification for workflow failures
3. Send to Slack/Email

## Advanced: Customize Rotation

### Change Rotation Frequency

The workflow rotates through all cities in order. To customize:

**Example: Rotate through top 5 cities weekly**

1. Edit "Set Variables" node
2. Change cities array to top 5
3. Workflow automatically cycles every 5 days

**Example: Different cities at different times**

Create multiple workflows:
- Workflow 1: Morning at 6am (West Coast cities)
- Workflow 2: Afternoon at 2pm (Central cities)
- Workflow 3: Evening at 10pm (East Coast cities)

### Add Conditional Logic

To skip cities without events:

1. After "Fetch Scraped Events" node
2. Add "If" node: check `eventCount > 0`
3. Only sync if events found

### Add Error Handling

To retry on failure:

1. After "Trigger Backend Scraper" node
2. Add error handler
3. Retry up to 3 times
4. If still fails, send error notification

## Monitoring & Maintenance

### Daily Monitoring

```bash
# Check if workflow ran
tail -f n8n_logs.txt | grep nocturne

# Expected output:
# 2026-02-05 00:00:00 - Nocturne Daily Scraper started
# 2026-02-05 00:00:05 - Triggering scraper for ca--los-angeles
# 2026-02-05 00:00:50 - Fetched 42 events
# 2026-02-05 00:00:51 - Synced to Supabase
```

### Weekly Maintenance

- [ ] Check execution success rate
- [ ] Verify event count trends
- [ ] Review Slack notifications
- [ ] Check Supabase table size

### Monthly Maintenance

- [ ] Review workflow performance
- [ ] Update city list if needed
- [ ] Check for API rate limiting issues
- [ ] Optimize wait times if needed

## Troubleshooting

### Workflow Not Running

**Check**:
1. Is workflow activated? (toggle should be ON)
2. Is n8n process running?
3. Check system logs for errors
4. Check n8n execution history for failures

**Fix**:
```bash
# Restart n8n
docker-compose restart n8n

# Or restart service
systemctl restart n8n
```

### Events Not Syncing to Supabase

**Check**:
1. Are Supabase credentials correct?
2. Does database have tables?
3. Are RLS policies allowing inserts?
4. Check n8n node output for errors

**Fix**:
1. Test Supabase connection separately
2. Verify API key has permission
3. Check table schema matches

### Slack Notifications Not Arriving

**Check**:
1. Is webhook URL correct?
2. Is Slack app authorized to channel?
3. Check n8n logs for HTTP errors

**Fix**:
1. Regenerate webhook URL
2. Authorize app to correct channel
3. Test webhook manually

## Performance Optimization

### Reduce Execution Time

Current time: ~50 seconds per city

To optimize:

1. **Reduce wait time** (if cities respond faster)
   - Edit "Wait for Scraper" node
   - Change 45s to 30s
   - Risk: Might miss events

2. **Reduce event limit** (if don't need 500)
   - Edit "Fetch Scraped Events" URL
   - Change `limit=500` to `limit=100`
   - Saves bandwidth

3. **Parallel execution** (multiple cities simultaneously)
   - Create separate workflows
   - Run at different times
   - Uses more n8n resources

### Reduce API Calls

Currently makes:
1. POST /scrape/{city_id}
2. GET /events/{city_id}
3. POST to Supabase
4. POST to Notion (optional)
5. POST to Slack (optional)

To reduce:
- Only sync if events > 0
- Skip failed cities
- Batch Slack notifications

## Cost Analysis

### Self-Hosted n8n
- Free to run
- Just needs server/container
- No per-execution cost

### n8n Cloud
- $20-$40/month depending on workflow complexity
- Unlimited executions

### Supabase Sync
- Free tier: 500k events
- 40 cities × 10k events = 400k events
- Fits in free tier

### Notion Sync
- Free (uses your Notion account)

### Slack Notifications
- Free

## Alternatives

### Self-Hosted Scheduler
Instead of n8n, could use:
- Cron job + Python script
- GitHub Actions
- AWS Lambda + EventBridge
- Jenkins + scheduling

### Backend Built-in Scheduler
Could add scheduler directly to Nocturne backend:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(scrape_all_cities, 'cron', hour=0, minute=0)
scheduler.start()
```

## Security Best Practices

1. **Don't commit secrets**
   - Use environment variables
   - Use n8n vault for sensitive data

2. **Rotate API keys regularly**
   - Monthly for Supabase
   - Monthly for Slack webhooks

3. **Use IP whitelisting** (if possible)
   - Restrict n8n IP in firewall

4. **Enable audit logging**
   - n8n logs all executions
   - Review for suspicious activity

5. **Use read-only credentials where possible**
   - Supabase: Use anon key (already limited)
   - Notion: Create separate integration for automation

## Next Steps

1. **Deploy**: Set up n8n instance
2. **Import**: Load workflow
3. **Configure**: Set environment variables
4. **Test**: Run workflow manually
5. **Activate**: Enable daily schedule
6. **Monitor**: Check executions

---

**n8n Version**: Tested on v1.0+  
**Workflow Version**: 1.0  
**Last Updated**: February 5, 2026
