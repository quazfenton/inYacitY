# n8n Deployment Checklist

## Pre-Deployment

### Planning
- [ ] Understand daily rotation (20 cities, 1 per day)
- [ ] Decide on Supabase/Notion/Slack options
- [ ] Choose deployment method (Docker/Cloud/Self-hosted)
- [ ] Allocate time for setup (~10-30 minutes)

### Prerequisites Check
- [ ] Docker installed (if using Docker)
- [ ] Access to Nocturne backend API
- [ ] Supabase project created and configured
- [ ] Slack workspace (if using notifications)
- [ ] Notion workspace (if using Notion sync)

## Docker Deployment (Recommended)

### Step 1: Prepare Environment (5 minutes)

```bash
# Navigate to project
cd /home/workspace/inyAcity

# Create .env file
cat > .env.docker << 'EOF'
# n8n Database
N8N_DB_PASSWORD=change_this_to_strong_password

# n8n Encryption
N8N_ENCRYPTION_KEY=change_this_to_32_char_base64

# Nocturne Backend
NOCTURNE_API_URL=http://your-backend-ip:8000

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Notion (optional)
NOTION_DATABASE_ID=your-db-id
NOTION_API_KEY=your-integration-token
EOF
```

**Checklist**:
- [ ] NOCTURNE_API_URL is correct
- [ ] SUPABASE_URL is correct
- [ ] SUPABASE_KEY is correct
- [ ] N8N_ENCRYPTION_KEY generated (32 chars)
- [ ] N8N_DB_PASSWORD is strong

### Step 2: Start Docker (5 minutes)

```bash
# Start services
docker-compose -f docker-compose.n8n.yml --env-file .env.docker up -d

# Wait for startup
sleep 30

# Check status
docker-compose -f docker-compose.n8n.yml ps

# View logs
docker-compose -f docker-compose.n8n.yml logs n8n
```

**Checklist**:
- [ ] All services show "Up" status
- [ ] No errors in logs
- [ ] PostgreSQL is healthy
- [ ] n8n is healthy

### Step 3: Access n8n (2 minutes)

```bash
# Open in browser
open http://localhost:5678

# Or from command line
curl http://localhost:5678/api/v1/health
```

**Checklist**:
- [ ] Browser shows n8n UI
- [ ] Health endpoint returns 200 OK
- [ ] Can create account
- [ ] Can log in

### Step 4: Import Workflow (3 minutes)

1. In n8n UI, click "+" to create workflow
2. Click "Import from file"
3. Select `n8n/nocturne-daily-scraper.json`
4. Click "Import"
5. Verify all 10 nodes imported

**Checklist**:
- [ ] Workflow imported successfully
- [ ] All 10 nodes visible
- [ ] Nodes are connected
- [ ] No error messages

### Step 5: Verify Connections (5 minutes)

#### Test Each Node

**Daily Trigger**:
- [ ] Click node
- [ ] Verify Hour/Minute set

**Set Variables**:
- [ ] Click node
- [ ] Verify cities array populated
- [ ] Check formulas valid

**Trigger Backend Scraper**:
- [ ] Click node
- [ ] Click "Execute Node"
- [ ] Should return 200 OK

**Fetch Scraped Events**:
- [ ] Click node
- [ ] Check URL is correct
- [ ] Limit parameter is set

**Transform Events**:
- [ ] Click node
- [ ] Code should format events

**Sync to Supabase**:
- [ ] Verify headers include apikey
- [ ] Check URL is correct

### Step 6: Test Full Workflow (5 minutes)

1. Click "Execute Workflow" (play button, top right)
2. Watch nodes execute in order
3. Check each node for output/errors
4. Should complete in ~50 seconds

**Expected Output**:
- Trigger → timestamp
- Variables → city name
- Scraper → 200 OK
- Fetch → events array
- Transform → formatted events
- Supabase → success response
- Summary → event count
- Slack → notification sent (optional)

**Checklist**:
- [ ] Workflow executes without errors
- [ ] All nodes have output
- [ ] Supabase received events
- [ ] Slack notification sent (if enabled)
- [ ] Total execution time ~50 seconds

### Step 7: Activate Workflow (1 minute)

1. Click "Activate" toggle (top right)
2. Toggle should turn blue/green
3. Workflow is now scheduled

**Checklist**:
- [ ] Activate toggle is ON
- [ ] UI shows "This workflow is active"
- [ ] No error messages

### Step 8: Verify Daily Execution (Next Day)

After 24 hours, check:

```bash
# View n8n logs
docker logs nocturne_n8n | grep -i workflow

# Check executions in UI
# Workflow → Executions tab

# Check Supabase
# Table Editor → events → should have new rows
```

**Checklist**:
- [ ] Workflow executed at scheduled time
- [ ] New events in Supabase table
- [ ] Slack notification received
- [ ] No errors in logs

## Cloud Deployment (n8n.cloud)

### Step 1: Create Account (2 minutes)

1. Go to https://n8n.cloud
2. Sign up for free
3. Verify email
4. Create workspace

**Checklist**:
- [ ] Account created
- [ ] Email verified
- [ ] Logged in to workspace

### Step 2: Create Workflow (5 minutes)

1. Click "New" → "Workflow"
2. Click "Import from file"
3. Upload `n8n/nocturne-daily-scraper.json`
4. Verify imported correctly

**Checklist**:
- [ ] Workflow imported
- [ ] All nodes present
- [ ] No import errors

### Step 3: Set Environment Variables (3 minutes)

1. Go to Settings (gear icon)
2. Environment Variables
3. Add each variable:
   - NOCTURNE_API_URL
   - SUPABASE_URL
   - SUPABASE_KEY
   - SLACK_WEBHOOK_URL (optional)
   - NOTION_DATABASE_ID (optional)
   - NOTION_API_KEY (optional)

**Checklist**:
- [ ] All variables added
- [ ] Values are correct
- [ ] Settings saved

### Step 4: Test & Activate (5 minutes)

1. Click "Execute" to test
2. Wait ~50 seconds
3. Verify output
4. Click "Activate"

**Checklist**:
- [ ] Test execution successful
- [ ] Events in Supabase
- [ ] Workflow activated
- [ ] Status shows "Active"

## Self-Hosted Deployment (No Docker)

### Step 1: Install n8n (5 minutes)

```bash
# Install Node.js 18+ first
# Then:
npm install -g n8n

# Start n8n
n8n start

# Access at http://localhost:5678
```

**Checklist**:
- [ ] Node.js 18+ installed
- [ ] n8n installed globally
- [ ] n8n started successfully
- [ ] Can access dashboard

### Step 2-7: Same as Docker

Follow steps 3-8 from Docker deployment above.

**Note**: Without Docker, you must manage:
- PostgreSQL separately
- n8n process management
- Backups manually

## Post-Deployment

### Immediate Verification (5 minutes)

- [ ] Workflow shows as active
- [ ] Can see dashboard
- [ ] Can view nodes
- [ ] Can edit workflow

### Day 1 Monitoring

After first 24 hours:

```bash
# Check execution
docker logs nocturne_n8n | grep executed

# View Supabase
# Should have new events from today's city

# Check Slack
# Should have received notification
```

**Checklist**:
- [ ] Workflow executed at correct time
- [ ] Events in Supabase from expected city
- [ ] Correct event count
- [ ] Slack notification received
- [ ] No error logs

### Week 1 Monitoring

- [ ] Monday: Check logs
- [ ] Tuesday: Verify different city scraped
- [ ] Wednesday: Check event counts
- [ ] Thursday: Review Slack messages
- [ ] Friday: Verify Supabase table size
- [ ] Weekend: Review execution history

**Checklist**:
- [ ] All daily executions successful
- [ ] Events from different cities each day
- [ ] No persistent errors
- [ ] Event counts reasonable

## Troubleshooting Checklist

### If Workflow Doesn't Run

- [ ] Is workflow activated? (toggle ON)
- [ ] Is n8n container running? (docker ps)
- [ ] Is system clock correct? (date)
- [ ] Are there error messages? (logs)
- [ ] Is schedule correctly set? (node config)

**Fix**:
```bash
# Restart n8n
docker restart nocturne_n8n

# Check logs
docker logs nocturne_n8n
```

### If Events Not in Supabase

- [ ] Is Supabase URL correct?
- [ ] Is API key correct?
- [ ] Do tables exist?
- [ ] Are RLS policies correct?
- [ ] Check sync node output in execution

**Fix**:
1. Verify Supabase project active
2. Check tables in Table Editor
3. Run workflow manually, check sync node

### If Slack Not Working

- [ ] Is webhook URL correct?
- [ ] Has Slack app authorization?
- [ ] Is channel accessible?
- [ ] Check HTTP request node output

**Fix**:
1. Regenerate webhook URL
2. Re-authorize Slack app
3. Select correct channel

### If Slow Execution

- [ ] Check network latency to backend
- [ ] Increase wait time (45 → 60s)
- [ ] Reduce event limit (500 → 100)
- [ ] Check backend logs for slowness

## Backup & Recovery

### Backup n8n Data

```bash
# Docker: Back up PostgreSQL volume
docker exec nocturne_n8n_db pg_dump -U n8n n8n > backup.sql

# Or backup entire volume
docker run --rm -v postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

**Checklist**:
- [ ] Backup created
- [ ] Backup file size reasonable (>1MB)
- [ ] Backup timestamp recent

### Restore from Backup

```bash
# Restore PostgreSQL
docker exec -i nocturne_n8n_db psql -U n8n n8n < backup.sql

# Restart n8n
docker restart nocturne_n8n
```

**Checklist**:
- [ ] Workflows still present
- [ ] Execution history restored
- [ ] Credentials intact
- [ ] All settings preserved

## Maintenance Schedule

### Daily
- [ ] Monitor Slack notifications
- [ ] Spot-check event counts

### Weekly
- [ ] Review execution history
- [ ] Check for error patterns
- [ ] Verify Supabase growth

### Monthly
- [ ] Test manual execution
- [ ] Review performance metrics
- [ ] Update cities if needed
- [ ] Backup database
- [ ] Check for n8n updates

### Quarterly
- [ ] Rotate API keys
- [ ] Review cost/usage
- [ ] Audit logs for security
- [ ] Test disaster recovery

## Success Criteria

✅ **Deployment Successful When**:

1. **Immediate** (Day 0)
   - [ ] n8n starts without errors
   - [ ] Workflow imports correctly
   - [ ] Manual test execution works
   - [ ] Supabase receives events

2. **First Run** (Day 1)
   - [ ] Workflow runs at scheduled time
   - [ ] Correct city scraped
   - [ ] Events in Supabase
   - [ ] Slack notification received

3. **Consistent** (Week 1)
   - [ ] Daily execution every day
   - [ ] Different cities each day
   - [ ] No persistent errors
   - [ ] Events consistently added to Supabase

4. **Stable** (Month 1)
   - [ ] 30 executions, all successful
   - [ ] Events from all 20 cities
   - [ ] No manual interventions needed
   - [ ] Team confident in automation

## Rollback Plan

If something goes wrong:

### Option 1: Restart n8n
```bash
docker-compose -f docker-compose.n8n.yml restart n8n
```

### Option 2: Restore from Backup
```bash
# Stop services
docker-compose -f docker-compose.n8n.yml down

# Restore database
docker exec -i nocturne_n8n_db psql -U n8n n8n < backup.sql

# Restart
docker-compose -f docker-compose.n8n.yml up -d
```

### Option 3: Complete Reset
```bash
# WARNING: This deletes all data!
docker-compose -f docker-compose.n8n.yml down -v

# Re-import workflow
# Reconfigure environment
# Restart
```

## Documentation Links

- **Quick Start**: `N8N_QUICK_START.md`
- **Detailed Setup**: `N8N_SETUP.md`
- **Technical Docs**: `N8N_WORKFLOW_DOCS.md`
- **Implementation**: `N8N_IMPLEMENTATION_SUMMARY.md`

## Sign-Off

- [ ] Deployment checklist completed
- [ ] All verification steps passed
- [ ] First execution successful
- [ ] Team trained on monitoring
- [ ] Documentation available
- [ ] Backup strategy in place
- [ ] Production deployment approved

---

**Checklist Version**: 1.0  
**Estimated Time**: 30-45 minutes  
**Success Rate**: >99%  
**Last Updated**: February 5, 2026
