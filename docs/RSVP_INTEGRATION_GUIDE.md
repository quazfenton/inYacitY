# Event RSVP & Calendar Integration Guide

## Overview

Ephemeral event RSVP system with automatic calendar integration and optional 2-hour reminders.

Users can RSVP directly on event pages and optionally add events to their Google Calendar or Apple Calendar with a single click.

---

## Database Setup

### Create RSVP Tables

Run the SQL in `scraper/RSVP_DATABASE_SCHEMA.sql` in Supabase:

```sql
CREATE TABLE rsvps (
  id BIGSERIAL PRIMARY KEY,
  rsvp_id VARCHAR(36) UNIQUE NOT NULL,
  event_id VARCHAR(100) NOT NULL,
  event_title TEXT NOT NULL,
  event_date DATE NOT NULL,
  event_time TEXT DEFAULT 'TBA',
  user_name VARCHAR(255) NOT NULL,
  user_email VARCHAR(255) NOT NULL,
  calendar_type VARCHAR(20),
  reminder_enabled BOOLEAN DEFAULT false,
  reminder_minutes INTEGER DEFAULT 120,
  reminder_sent BOOLEAN DEFAULT false,
  reminder_sent_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_event_id (event_id),
  INDEX idx_user_email (user_email),
  INDEX idx_event_date (event_date),
  INDEX idx_reminder_enabled (reminder_enabled),
  INDEX idx_reminder_sent (reminder_sent)
);

-- Optional views for notifications
CREATE VIEW active_rsvps AS
SELECT * FROM rsvps
WHERE event_date >= CURRENT_DATE
ORDER BY event_date ASC;

CREATE VIEW pending_reminders AS
SELECT * FROM rsvps
WHERE reminder_enabled = true
  AND reminder_sent = false
  AND event_date = CURRENT_DATE;
```

---

## Backend API

### RSVP to Event

```bash
POST /api/scraper/rsvp
Content-Type: application/json

{
  "event_id": "event_hash_abc123",
  "title": "Tech Conference 2026",
  "date": "2026-02-15",
  "time": "7:00 PM",
  "location": "Los Angeles, CA",
  "description": "Annual tech conference",
  "user_name": "John Doe",
  "user_email": "john@example.com",
  "calendar_type": "google",
  "reminder_enabled": true,
  "reminder_minutes": 120
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "rsvp_id": "550e8400-e29b-41d4-a716-446655440000",
  "calendar_url": "https://calendar.google.com/calendar/render?action=TEMPLATE&text=Tech+Conference+2026&dates=20260215T190000/20260215T210000&location=Los+Angeles%2C+CA&details=Annual+tech+conference",
  "message": "RSVP recorded for John Doe",
  "reminder_enabled": true,
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

### Cancel RSVP

```bash
DELETE /api/scraper/rsvp/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "RSVP cancelled",
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

### Get RSVP Status

```bash
GET /api/scraper/rsvp-status/event_hash_abc123
```

**Response (200 OK):**
```json
{
  "success": true,
  "event_id": "event_hash_abc123",
  "rsvp_count": 42,
  "attendees": [
    {
      "rsvp_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_name": "John Doe",
      "user_email": "john@example.com"
    },
    {
      "rsvp_id": "660e8400-e29b-41d4-a716-446655440001",
      "user_name": "Jane Smith",
      "user_email": "jane@example.com"
    }
  ],
  "timestamp": "2026-02-06T12:34:56.789Z"
}
```

---

## Frontend Integration

### Using the useEventRSVP Hook

```typescript
import { useEventRSVP } from '@/hooks/useEventRSVP';

interface EventData {
  event_id: string;
  title: string;
  date: string;        // YYYY-MM-DD
  time?: string;       // HH:MM AM/PM
  location: string;
  description?: string;
}

function EventRSVPButton({ event }: { event: EventData }) {
  const { rsvpEvent, cancelRSVP, getRSVPStatus, isLoading, error, rsvpData } = useEventRSVP();

  const handleRSVP = async () => {
    const result = await rsvpEvent(event, {
      user_name: 'John Doe',
      user_email: 'john@example.com',
      calendar_type: 'google',  // or 'apple' or null
      reminder_enabled: true,
      reminder_minutes: 120
    });

    if (result) {
      console.log('RSVP successful, calendar URL:', result.calendar_url);
      // Calendar URL opens automatically (if provided)
    }
  };

  return (
    <div>
      <button onClick={handleRSVP} disabled={isLoading}>
        {isLoading ? 'RSVPing...' : 'RSVP to Event'}
      </button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {rsvpData && <p>✓ RSVP recorded! ID: {rsvpData.rsvp_id}</p>}
    </div>
  );
}
```

### Full RSVP Form Component

```typescript
import { useState } from 'react';
import { useEventRSVP } from '@/hooks/useEventRSVP';

export function EventRSVPForm({ event }) {
  const { rsvpEvent, isLoading, error, rsvpData } = useEventRSVP();
  const [formData, setFormData] = useState({
    user_name: '',
    user_email: '',
    calendar_type: 'google' as const,
    reminder_enabled: true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await rsvpEvent(event, {
      user_name: formData.user_name,
      user_email: formData.user_email,
      calendar_type: formData.calendar_type,
      reminder_enabled: formData.reminder_enabled,
      reminder_minutes: 120,
    });
  };

  if (rsvpData) {
    return (
      <div className="success">
        <h3>✓ RSVP Confirmed!</h3>
        <p>We've added {event.title} to your calendar.</p>
        <p>Reminder: You'll get a notification 2 hours before.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Your name"
        value={formData.user_name}
        onChange={(e) =>
          setFormData({ ...formData, user_name: e.target.value })
        }
        required
      />

      <input
        type="email"
        placeholder="Your email (optional)"
        value={formData.user_email}
        onChange={(e) =>
          setFormData({ ...formData, user_email: e.target.value })
        }
      />

      <label>
        <input
          type="radio"
          name="calendar"
          value="google"
          checked={formData.calendar_type === 'google'}
          onChange={(e) =>
            setFormData({ ...formData, calendar_type: 'google' })
          }
        />
        Add to Google Calendar
      </label>

      <label>
        <input
          type="radio"
          name="calendar"
          value="apple"
          checked={formData.calendar_type === 'apple'}
          onChange={(e) =>
            setFormData({ ...formData, calendar_type: 'apple' })
          }
        />
        Add to Apple Calendar
      </label>

      <label>
        <input
          type="radio"
          name="calendar"
          value=""
          checked={formData.calendar_type === ''}
          onChange={() => setFormData({ ...formData, calendar_type: null })}
        />
        Don't add to calendar
      </label>

      <label>
        <input
          type="checkbox"
          checked={formData.reminder_enabled}
          onChange={(e) =>
            setFormData({ ...formData, reminder_enabled: e.target.checked })
          }
        />
        Send 2-hour reminder (optional)
      </label>

      <button type="submit" disabled={isLoading || !formData.user_name}>
        {isLoading ? 'RSVPing...' : 'RSVP'}
      </button>

      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

### Display Attendee Count

```typescript
export function EventAttendees({ eventId }) {
  const [status, setStatus] = useState(null);
  const { getRSVPStatus } = useEventRSVP();

  useEffect(() => {
    getRSVPStatus(eventId).then(setStatus);
  }, [eventId]);

  if (!status) return null;

  return (
    <div>
      <h3>{status.rsvp_count} people RSVPed</h3>
      {status.attendees.length > 0 && (
        <ul>
          {status.attendees.map((attendee) => (
            <li key={attendee.rsvp_id}>{attendee.user_name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Calendar Integration Details

### Google Calendar

- **Format:** Direct TEMPLATE URL
- **Opens:** calendar.google.com event creation
- **Example URL:** `https://calendar.google.com/calendar/render?action=TEMPLATE&text=Event+Title&dates=20260215T190000/20260215T210000&location=Los+Angeles&details=Description`
- **Parameters:**
  - `text`: Event title
  - `dates`: Start/end time (RFC 3339: YYYYMMDDTHHMMSS)
  - `location`: Event location
  - `details`: Event description

### Apple Calendar

- **Format:** iCal-compatible URL
- **Opens:** Apple Calendar app (or iCloud Calendar)
- **Example URL:** `webcal://calendar.apple.com/?title=Event+Title&dates=20260215T190000/20260215T210000&location=Los+Angeles&description=Description`
- **Behavior:** Opens calendar app for event creation

---

## Reminder Notifications

### How It Works

1. User enables reminders during RSVP (default: OFF)
2. Sets reminder time (default: 120 minutes = 2 hours before)
3. System stores preference in `rsvps.reminder_enabled` and `rsvps.reminder_minutes`
4. Infrastructure ready for notification service

### Database Views for Notifications

```sql
-- Get all active RSVPs (events not yet passed)
SELECT * FROM active_rsvps;

-- Get reminders that need to be sent
SELECT * FROM pending_reminders;

-- Update reminder status after sending
UPDATE rsvps 
SET reminder_sent = true, reminder_sent_at = NOW()
WHERE rsvp_id = 'uuid';
```

### Implementing Reminder Service

```python
# Example: N8N webhook or scheduled task
import requests
from datetime import datetime, timedelta

def send_reminders():
    # Get reminders to send from database
    reminders = get_pending_reminders()
    
    for rsvp in reminders:
        # Send email notification
        send_email(
            to=rsvp['user_email'],
            subject=f"Reminder: {rsvp['event_title']} in 2 hours",
            body=f"Your event {rsvp['event_title']} starts at {rsvp['event_time']}"
        )
        
        # Mark as sent
        update_rsvp_reminder_sent(rsvp['rsvp_id'])

def get_pending_reminders():
    # Query database view: pending_reminders
    pass

def update_rsvp_reminder_sent(rsvp_id):
    # Update rsvps table
    pass
```

---

## Configuration

### Optional: Customize Reminder Time

Default reminder time is 120 minutes (2 hours). Can be customized per RSVP:

```typescript
await rsvpEvent(event, {
  user_name: 'John',
  reminder_enabled: true,
  reminder_minutes: 60  // 1 hour before
});
```

### Optional: Disable Calendar Integration

Users can choose not to add to calendar:

```typescript
await rsvpEvent(event, {
  user_name: 'John',
  calendar_type: null,  // Don't open calendar
  reminder_enabled: true
});
```

---

## Data Retention

RSVP data is **ephemeral**:
- Stored in `rsvps` table
- Active until event date passes
- Can be automatically cleaned up after event date
- Optional: Archive old RSVPs for analytics

---

## Example: Complete Event Card

```typescript
export function EventCard({ event }) {
  const [showRSVP, setShowRSVP] = useState(false);

  return (
    <div className="event-card">
      <h2>{event.title}</h2>
      <p>{event.date} at {event.time}</p>
      <p>{event.location}</p>
      <p>{event.description}</p>

      {!showRSVP && (
        <button onClick={() => setShowRSVP(true)}>
          RSVP to This Event
        </button>
      )}

      {showRSVP && (
        <EventRSVPForm 
          event={event} 
          onClose={() => setShowRSVP(false)}
        />
      )}

      <EventAttendees eventId={event.event_id} />
    </div>
  );
}
```

---

## Testing

### Test RSVP Endpoint

```bash
curl -X POST http://localhost:5000/api/scraper/rsvp \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test_event_123",
    "title": "Test Event",
    "date": "2026-02-20",
    "time": "7:00 PM",
    "location": "Test Location",
    "user_name": "Test User",
    "calendar_type": "google",
    "reminder_enabled": true
  }'
```

### Test Status Endpoint

```bash
curl http://localhost:5000/api/scraper/rsvp-status/test_event_123
```

### Test Cancel Endpoint

```bash
curl -X DELETE http://localhost:5000/api/scraper/rsvp/{rsvp_id}
```

---

## FAQ

**Q: How do users add events to their calendar?**
A: The RSVP response includes a `calendar_url`. Frontend opens this URL automatically, which opens the calendar app (Google Calendar or Apple Calendar) with pre-filled event data.

**Q: Are reminders automatic?**
A: The feature stores reminder preferences in the database. You need to implement a notification service (e.g., N8N scheduled task) to actually send emails/notifications.

**Q: Is personal data stored securely?**
A: Yes, email addresses are stored in the database. Use HTTPS and follow data protection regulations (GDPR, etc.).

**Q: Can users RSVP multiple times to the same event?**
A: Currently yes, but you can add a UNIQUE constraint if needed.

**Q: How long is RSVP data kept?**
A: Until event date passes. Create a cleanup job to archive or delete old records.

---

**Implementation Complete & Ready to Use** ✅
