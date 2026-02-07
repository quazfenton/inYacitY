-- Comments table for event discussions
-- Ephemeral: Comments can be moderated or deleted after event passes

CREATE TABLE IF NOT EXISTS comments (
  id BIGSERIAL PRIMARY KEY,
  comment_id VARCHAR(36) UNIQUE NOT NULL,
  event_id VARCHAR(100) NOT NULL,
  author_name VARCHAR(255) NOT NULL,
  author_email VARCHAR(255),
  author_ip VARCHAR(50),
  text TEXT NOT NULL,
  likes INTEGER DEFAULT 0,
  is_approved BOOLEAN DEFAULT true,
  is_deleted BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_event_id FOREIGN KEY (event_id) REFERENCES events(event_hash)
);
);

-- Optional: Create a view for active comments (not deleted, approved, event not passed)
CREATE OR REPLACE VIEW active_comments AS
SELECT c.* FROM comments c
JOIN events e ON c.event_id = e.event_hash
WHERE c.is_deleted = false
  AND c.is_approved = true
  AND e.date >= CURRENT_DATE
ORDER BY c.created_at DESC;

-- Optional: Create a view for moderation queue (unapproved comments)
CREATE OR REPLACE VIEW comment_moderation_queue AS
SELECT * FROM comments
WHERE is_approved = false
  AND is_deleted = false
ORDER BY created_at ASC;

-- Optional: Statistics view
CREATE OR REPLACE VIEW comment_statistics AS
SELECT 
  event_id,
  COUNT(*) as total_comments,
  SUM(CASE WHEN is_approved = true AND is_deleted = false THEN 1 ELSE 0 END) as approved_comments,
  SUM(likes) as total_likes,
  MAX(created_at) as latest_comment
FROM comments
GROUP BY event_id;
