-- RSVP Table for Event Attendance Tracking
-- Ephemeral: Records user RSVPs with optional calendar integration and reminders

CREATE TABLE IF NOT EXISTS rsvps (
  id BIGSERIAL PRIMARY KEY,
  rsvp_id VARCHAR(36) UNIQUE NOT NULL,
  event_id VARCHAR(100) NOT NULL,
  event_title TEXT NOT NULL,
  event_date DATE NOT NULL,
  event_time TEXT DEFAULT 'TBA',
  user_name VARCHAR(255) NOT NULL,
  user_email VARCHAR(255) NOT NULL,
  calendar_type VARCHAR(20),  -- 'google', 'apple', or NULL
  reminder_enabled BOOLEAN DEFAULT false,
  reminder_minutes INTEGER DEFAULT 120,
  reminder_sent BOOLEAN DEFAULT false,
  reminder_sent_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_event_id ON rsvps (event_id);
CREATE INDEX IF NOT EXISTS idx_user_email ON rsvps (user_email);
CREATE INDEX IF NOT EXISTS idx_event_date ON rsvps (event_date);
CREATE INDEX IF NOT EXISTS idx_reminder_enabled ON rsvps (reminder_enabled);
CREATE INDEX IF NOT EXISTS idx_reminder_sent ON rsvps (reminder_sent);

-- Optional: Create a view for active RSVPs (not yet expired)
CREATE OR REPLACE VIEW active_rsvps AS
SELECT * FROM rsvps
WHERE event_date >= CURRENT_DATE
ORDER BY event_date ASC;

-- Optional: Create a view for reminders to be sent
CREATE OR REPLACE VIEW pending_reminders AS
SELECT * FROM rsvps
WHERE reminder_enabled = true
  AND reminder_sent = false
  AND event_date = CURRENT_DATE
  AND CAST(CONCAT(event_date, ' ', COALESCE(event_time, '00:00')) AS DATETIME) 
      <= DATE_SUB(NOW(), INTERVAL reminder_minutes MINUTE)
ORDER BY event_date, event_time;
