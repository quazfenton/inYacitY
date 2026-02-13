# Weekly Email Digest System

Complete system for sending weekly event digests to subscribers, filtering out past events.

## Overview

The weekly digest system automatically:
1. Gathers upcoming events for each city (next 7 days by default)
2. Filters out past events automatically
3. Maps events to subscribers by city
4. Sends emails with rate limiting and batching
5. Logs all email activity

## Files

- `backend/weekly_digest.py` - Main digest sending script
- `backend/database.py` - Updated with helper functions
- `backend/email_service.py` - Email templates and sending

## Features

### Event Filtering
- **No Past Events**: Only future events are included (from today onwards)
- **Configurable Window**: Default 7 days, customizable
- **City-Specific**: Events matched to subscriber's registered city

### Email Sending
- **Rate Limiting**: Configurable batch size and delays
- **Error Handling**: Failed sends are logged and reported
- **Email Logging**: All sends tracked in `email_logs` table
- **Multiple Providers**: SMTP and SendGrid support

### Batching & Performance
- **Batch Processing**: Send emails in configurable batches (default: 10)
- **Delay Between Batches**: Prevent rate limiting (default: 1 second)
- **Concurrent Sends**: Emails within a batch sent concurrently
- **Progress Tracking**: Real-time progress output

## Quick Start

### 1. Test Mode (Dry Run)

Preview what would be sent without actually sending:

```bash
cd backend
python weekly_digest.py --dry-run
```

### 2. Test Send to Single Email

Send a test digest to yourself:

```bash
python weekly_digest.py --test your@email.com
```

### 3. Send for Specific City

Process only one city:

```bash
python weekly_digest.py --send --city ca--los-angeles
```

### 4. Send All Digests

Send to all subscribers (production):

```bash
python weekly_digest.py --send
```

## Command Reference

### Basic Commands

```bash
# Preview (dry run)
python weekly_digest.py --dry-run

# Send all digests
python weekly_digest.py --send

# Send for specific city only
python weekly_digest.py --send --city ca--los-angeles

# Test to single email
python weekly_digest.py --test user@example.com
```

### Advanced Options

```bash
# Custom date range (next 14 days)
python weekly_digest.py --send --days 14

# Smaller batches with longer delay (gentle rate limiting)
python weekly_digest.py --send --batch-size 5 --delay 2.0

# Limit events per email
python weekly_digest.py --send --max-events 15

# Combine options
python weekly_digest.py --send --city ny--new-york --days 14 --batch-size 5
```

### Option Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--send` | Actually send emails (required) | - |
| `--dry-run` | Preview without sending | - |
| `--city` | Process only specific city | All cities |
| `--days` | Days ahead to include events | 7 |
| `--test` | Send test to single email | - |
| `--batch-size` | Emails per batch | 10 |
| `--delay` | Seconds between batches | 1.0 |
| `--max-events` | Max events per email | 20 |

## Scheduling

### Cron Job (Weekly)

Add to crontab to run every Monday at 9 AM:

```bash
# Edit crontab
crontab -e

# Add line:
0 9 * * 1 cd /app && python backend/weekly_digest.py --send >> /var/log/weekly_digest.log 2>&1
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  weekly-digest:
    build: .
    command: python backend/weekly_digest.py --send
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
    depends_on:
      - db
    profiles:
      - cron  # Only run when explicitly invoked
```

Run with:
```bash
docker-compose --profile cron run weekly-digest
```

## Database Schema

### Events Table

Events are automatically filtered by date:

```sql
-- Get only future events
SELECT * FROM events 
WHERE date >= CURRENT_DATE 
ORDER BY date;
```

### Subscriptions Table

Subscribers linked to cities:

```sql
-- Get active subscribers for a city
SELECT email FROM subscriptions 
WHERE city = 'ca--los-angeles' 
AND is_active = true;
```

### Email Logs Table

Track all email activity:

```sql
-- View recent sends
SELECT * FROM email_logs 
ORDER BY sent_at DESC 
LIMIT 20;

-- Check for failures
SELECT * FROM email_logs 
WHERE success = false 
ORDER BY sent_at DESC;
```

## How It Works

### 1. Event Gathering

```python
# Get events from today onwards (no past events)
events = await get_future_events_for_city(
    city='ca--los-angeles',
    start_date=date.today(),  # Only future events
    end_date=date.today() + timedelta(days=7),
    limit=20
)
```

### 2. Subscriber Mapping

```python
# Get subscribers for the city
subscribers = await get_subscribers_by_city('ca--los-angeles')

# Each subscriber gets events for their registered city
```

### 3. Rate-Limited Sending

```python
# Send in batches with delays
for batch in batches_of(subscribers, batch_size=10):
    # Send batch concurrently
    await asyncio.gather(*[
        send_email(sub.email, content) 
        for sub in batch
    ])
    
    # Wait before next batch
    await asyncio.sleep(1.0)
```

### 4. Logging

Every send attempt is logged:
- Success/failure status
- Number of events
- Error messages
- Timestamp

## Output Example

```
============================================================
WEEKLY EMAIL DIGEST
============================================================
Mode: LIVE (sending emails)
Days ahead: 7
Batch size: 10
Delay between batches: 1.0s
============================================================

[INFO] Found 3 cities with active subscribers

[PROCESSING] City: ca--los-angeles
============================================================
City Name: Los Angeles
[GATHER] Fetching events for ca--los-angeles (next 7 days)...
[GATHER] Found 12 upcoming events for ca--los-angeles
[INFO] Sending to 45 subscribers

[BATCH] Sending batch 1/5
  [SENT] Digest to user1@example.com (12 events)
  [SENT] Digest to user2@example.com (12 events)
  ...
  [RATE-LIMIT] Waiting 1.0s before next batch...

[RESULT] ca--los-angeles:
  Emails sent: 45
  Emails failed: 0
  Events included: 12

============================================================
DIGEST COMPLETE
============================================================
Total cities processed: 3
Total emails sent: 127
Total emails failed: 0
Total events included: 34
Duration: 15.3 seconds
============================================================
```

## Email Template

The weekly digest email includes:

- **Header**: City name with Nocturne branding
- **Event List**: Up to 20 events (configurable)
  - Title
  - Date and time
  - Location
  - Truncated description
  - Link to event
- **Footer**: Unsubscribe link

Template location: `backend/email_service.py`

## Cleanup of Past Events

To keep the database clean, past events are automatically filtered out:

### When Gathering Events

```python
# Only events from today onwards
events = await get_upcoming_events(
    city='ca--los-angeles',
    days_ahead=7  # This week only
)
```

### Optional: Periodic Cleanup

Remove old events from database:

```python
# Remove events older than 30 days
deleted = await cleanup_past_events(days_to_keep=30)
print(f"Deleted {deleted} old events")
```

## Monitoring

### Check Email Logs

```sql
-- Total emails sent this week
SELECT COUNT(*) FROM email_logs 
WHERE sent_at >= CURRENT_DATE - INTERVAL '7 days';

-- Success rate
SELECT 
    success, 
    COUNT(*) 
FROM email_logs 
WHERE sent_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY success;

-- Emails by city
SELECT city, COUNT(*) 
FROM email_logs 
WHERE sent_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY city 
ORDER BY COUNT(*) DESC;
```

### Log File

If running via cron, check logs:

```bash
# View latest run
tail -n 50 /var/log/weekly_digest.log

# Check for errors
grep "ERROR" /var/log/weekly_digest.log

# Count sent emails
grep "Emails sent:" /var/log/weekly_digest.log
```

## Troubleshooting

### "No email service configured"

Set environment variables:
```bash
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
# OR
export SENDGRID_API_KEY="your-api-key"
```

### "No events found"

Check if events exist:
```bash
# Query database
python -c "
import asyncio
from database import get_upcoming_events
events = asyncio.run(get_upcoming_events('ca--los-angeles', 7))
print(f'Found {len(events)} events')
"
```

### "No subscribers found"

Check subscriptions:
```sql
SELECT city, COUNT(*) 
FROM subscriptions 
WHERE is_active = true 
GROUP BY city;
```

### Rate Limiting Issues

If emails are being rejected:
```bash
# Reduce batch size and increase delay
python weekly_digest.py --send --batch-size 5 --delay 3.0
```

### Test Mode Not Sending

Test mode only sends to one email:
```bash
# Correct usage
python weekly_digest.py --test your@email.com
```

## API Integration

You can also trigger digests via API:

```python
from backend.weekly_digest import WeeklyDigestSender

async def send_digest():
    sender = WeeklyDigestSender(days_ahead=7)
    await sender.send_all_digests()

# Run
asyncio.run(send_digest())
```

## Best Practices

1. **Always test first**:
   ```bash
   python weekly_digest.py --dry-run
   python weekly_digest.py --test your@email.com
   ```

2. **Schedule during low-traffic hours** (early morning)

3. **Monitor logs** after each run

4. **Set up alerts** for failures

5. **Keep email list clean**:
   ```sql
   -- Unsubscribe bounced emails
   UPDATE subscriptions 
   SET is_active = false 
   WHERE email IN (SELECT email FROM bounces);
   ```

## Security

- SMTP credentials stored in environment variables
- No credentials in code or logs
- HTTPS required for email links
- Unsubscribe links in all emails
- Rate limiting prevents abuse

## Future Enhancements

- [ ] Personalization (user name in email)
- [ ] Event recommendations based on history
- [ ] A/B testing for subject lines
- [ ] Open/click tracking
- [ ] Automated bounce handling
- [ ] Preference center (frequency, categories)

## Support

For issues:
1. Check `email_logs` table for errors
2. Review `/var/log/weekly_digest.log`
3. Verify SMTP/SendGrid credentials
4. Test with `--dry-run` and `--test`

Part of the Nocturne Event Platform.
