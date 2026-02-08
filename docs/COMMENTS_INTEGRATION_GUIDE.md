# Event Comments System Integration Guide

## Overview

Ephemeral event comment system with built-in rate limiting to prevent spam. Comments are moderated and tied to individual events.

Users can post comments, like comments, and view discussion threads for each event.

---

## Database Setup
CREATE TABLE comments (
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
  FOREIGN KEY (event_id) REFERENCES events(event_hash)
);

CREATE INDEX idx_event_id ON comments(event_id);
CREATE INDEX idx_author_email ON comments(author_email);
CREATE INDEX idx_created_at ON comments(created_at);
CREATE INDEX idx_is_approved ON comments(is_approved);
CREATE INDEX idx_is_deleted ON comments(is_deleted);
);

-- Views for moderation and analytics
CREATE VIEW active_comments AS
SELECT c.* FROM comments c
JOIN events e ON c.event_id = e.event_hash
WHERE c.is_deleted = false
  AND c.is_approved = true
  AND e.date >= CURRENT_DATE
ORDER BY c.created_at DESC;

CREATE VIEW comment_moderation_queue AS
SELECT * FROM comments
WHERE is_approved = false
  AND is_deleted = false
ORDER BY created_at ASC;

CREATE VIEW comment_statistics AS
SELECT 
  event_id,
  COUNT(*) as total_comments,
  SUM(CASE WHEN is_approved = true AND is_deleted = false THEN 1 ELSE 0 END) as approved_comments,
  SUM(likes) as total_likes,
  MAX(created_at) as latest_comment
FROM comments
GROUP BY event_id;
```

---

## Rate Limiting

### How It Works

Comments are rate-limited per IP address:

- **3 comments per minute** - Prevents rapid-fire spamming
- **20 comments per hour** - Prevents bulk comment attacks
- **100 comments per day** - Reasonable daily limit

When a user hits a limit, they get a helpful message with wait time.

### Configuration

Limits can be customized in `backend/api/scraper_api.py`:

```python
self._rate_limiter = RateLimiter(
    max_per_minute=3,      # Change this
    max_per_hour=20,       # Or this
    max_per_day=100        # Or this
)
```

### Rate Limit Responses

**Normal POST:**
```json
{
  "success": true,
  "comment_id": "uuid",
  "message": "Comment posted successfully"
}
```

**Rate Limited (429 Too Many Requests):**
```json
{
  "success": false,
  "message": "Too many comments. Please wait 45 seconds.",
  "rate_limited": true
}
```

---

## Backend API

### Get Comments for Event

```bash
GET /api/scraper/comments/{event_id}?limit=50&offset=0&approved=true

Query Parameters:
  - limit: max 500 comments (default: 50)
  - offset: pagination offset (default: 0)
  - approved: only show approved comments (default: true)
```

**Response (200 OK):**
```json
{
  "success": true,
  "event_id": "event_hash_123",
  "comments": [
    {
      "comment_id": "uuid-123",
      "author_name": "John Doe",
      "text": "This event was amazing!",
      "created_at": "2026-02-06T12:34:56Z",
      "updated_at": null,
      "likes": 5,
      "is_approved": true
    },
    {
      "comment_id": "uuid-456",
      "author_name": "Jane Smith",
      "text": "Great organization and venue!",
      "created_at": "2026-02-06T13:00:00Z",
      "likes": 3,
      "is_approved": true
    }
  ],
  "total_count": 42,
  "limit": 50,
  "offset": 0,
  "timestamp": "2026-02-06T14:00:00Z"
}
```

### Post Comment

```bash
POST /api/scraper/comments
Content-Type: application/json

{
  "event_id": "event_hash_123",
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "text": "This event was amazing!"
}
```

**Validation:**
- Text: 3-1000 characters
- Author name: required, max 255 chars
- Event ID: required
- Email: optional

**Rate Limiting:**
- 3 per minute per IP
- 20 per hour per IP
- 100 per day per IP

**Response (201 Created):**
```json
{
  "success": true,
  "comment_id": "uuid-789",
  "message": "Comment posted successfully",
  "is_approved": true,
  "timestamp": "2026-02-06T14:05:00Z"
}
```

**If Rate Limited (429 Too Many Requests):**
```json
{
  "success": false,
  "message": "Too many comments. Please wait 45 seconds.",
  "rate_limited": true
}
```

### Like Comment

```bash
POST /api/scraper/comments/{comment_id}/like
```

**Response (200 OK):**
```json
{
  "success": true,
  "comment_id": "uuid-123",
  "likes": 6,
  "timestamp": "2026-02-06T14:10:00Z"
}
```

### Delete Comment

```bash
DELETE /api/scraper/comments/{comment_id}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Comment deleted",
  "timestamp": "2026-02-06T14:15:00Z"
}
```

### Check Rate Limit Status

```bash
GET /api/scraper/comments/rate-limit/status
```

**Response (200 OK):**
```json
{
  "success": true,
  "rate_limit": {
    "comments_this_minute": 2,
    "comments_this_hour": 8,
    "comments_today": 25,
    "limit_per_minute": 3,
    "limit_per_hour": 20,
    "limit_per_day": 100
  },
  "timestamp": "2026-02-06T14:00:00Z"
}
```

---

## Frontend Integration

### Using the useEventComments Hook

```typescript
import { useEventComments } from '@/hooks/useEventComments';
import { useEffect } from 'react';

function EventCommentsSection({ eventId }: { eventId: string }) {
  const {
    comments,
    totalCount,
    isLoading,
    error,
    rateLimitStatus,
    fetchComments,
    postComment,
    deleteComment,
    likeComment,
  } = useEventComments();

  useEffect(() => {
    fetchComments(eventId);
  }, [eventId, fetchComments]);

  const handlePostComment = async (authorName: string, text: string) => {
    const result = await postComment(eventId, authorName, text);
    if (result?.success) {
      // Refresh comments
      await fetchComments(eventId);
    }
  };

  return (
    <div>
      <h3>Comments ({totalCount})</h3>
      
      {rateLimitStatus && (
        <p>
          {rateLimitStatus.comments_this_minute}/{rateLimitStatus.limit_per_minute} comments this minute
        </p>
      )}

      {/* Comment form */}
      <CommentForm
        onSubmit={handlePostComment}
        disabled={
          rateLimitStatus &&
          rateLimitStatus.comments_this_minute >= rateLimitStatus.limit_per_minute
        }
      />

      {/* Comments list */}
      <div>
        {comments.map((comment) => (
          <CommentCard
            key={comment.comment_id}
            comment={comment}
            onLike={() => likeComment(comment.comment_id)}
            onDelete={() => deleteComment(comment.comment_id)}
          />
        ))}
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
```

### Complete Comment Form Component

```typescript
import { useState } from 'react';
import { useEventComments } from '@/hooks/useEventComments';

export function EventCommentForm({ eventId }: { eventId: string }) {
  const { postComment, isLoading, error, rateLimitStatus } = useEventComments();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [text, setText] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const result = await postComment(eventId, name, text, email);

    if (result?.success) {
      setName('');
      setEmail('');
      setText('');
      // Show success message
    }
  };

  const canPost =
    rateLimitStatus &&
    rateLimitStatus.comments_this_minute < rateLimitStatus.limit_per_minute;

  return (
    <form onSubmit={handleSubmit} className="comment-form">
      <input
        type="text"
        placeholder="Your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        maxLength={255}
      />

      <input
        type="email"
        placeholder="Email (optional)"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <textarea
        placeholder="Share your thoughts about this event..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        required
        minLength={3}
        maxLength={1000}
        disabled={!canPost || isLoading}
      />

      <div className="form-footer">
        <button
          type="submit"
          disabled={!canPost || isLoading || !name || !text}
        >
          {isLoading ? 'Posting...' : 'Post Comment'}
        </button>

        {rateLimitStatus && (
          <span className="rate-limit">
            {rateLimitStatus.comments_this_minute}/
            {rateLimitStatus.limit_per_minute} this minute
          </span>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
          {error.includes('wait') && (
            <p className="help-text">Try again in a moment</p>
          )}
        </div>
      )}
    </form>
  );
}
```

### Comment Card Component

```typescript
interface CommentCardProps {
  comment: Comment;
  onLike: () => void;
  onDelete: () => void;
}

export function CommentCard({
  comment,
  onLike,
  onDelete,
}: CommentCardProps) {
  const createdDate = new Date(comment.created_at);
  const isUpdated = comment.updated_at !== null;

  return (
    <div className="comment-card">
      <div className="comment-header">
        <h4 className="comment-author">{comment.author_name}</h4>
        <time className="comment-date" dateTime={comment.created_at}>
          {createdDate.toLocaleDateString()} at{' '}
          {createdDate.toLocaleTimeString()}
        </time>
        {isUpdated && <span className="comment-edited">(edited)</span>}
      </div>

      <p className="comment-text">{comment.text}</p>

      <div className="comment-actions">
        <button onClick={onLike} className="like-button">
          👍 {comment.likes}
        </button>

        <button onClick={onDelete} className="delete-button">
          🗑️ Delete
        </button>
      </div>

      {!comment.is_approved && (
        <div className="comment-pending">
          Pending moderation...
        </div>
      )}
    </div>
  );
}
```

---

## Moderation

### Approve Comments

Comments are auto-approved by default. To require moderation, change in `scraper_api.py`:

```python
# From:
is_approved = True

# To:
is_approved = False  # Require manual approval
```

### Query Pending Comments

```sql
SELECT * FROM comment_moderation_queue;
```

### Approve Comment

```sql
UPDATE comments SET is_approved = true WHERE comment_id = 'uuid';
```

### Block User by IP

```sql
-- Soft delete all comments from IP
UPDATE comments 
SET is_deleted = true 
WHERE author_ip = '192.168.1.1';

-- Or add to blocklist (you'd create this table)
INSERT INTO blocked_ips (ip_address, reason) 
VALUES ('192.168.1.1', 'Spam');
```

---

## Analytics

### Get Comment Statistics

```sql
SELECT * FROM comment_statistics;
```

### Popular Comments

```sql
SELECT * FROM comments
WHERE is_deleted = false
ORDER BY likes DESC
LIMIT 10;
```

### Recent Comments

```sql
SELECT * FROM active_comments
LIMIT 20;
```

---

## Data Retention

Comments are **ephemeral**:
- Stored until manually deleted
- Soft delete (marked as deleted, not removed)
- Can query deleted comments with `WHERE is_deleted = true`
- Optional: Archive old comments periodically

---

## Example: Complete Event Comments Section

```typescript
import { useEventComments } from '@/hooks/useEventComments';
import { useEffect, useState } from 'react';

export function EventCommentsSection({ eventId }: { eventId: string }) {
  const {
    comments,
    totalCount,
    isLoading,
    rateLimitStatus,
    fetchComments,
    postComment,
    deleteComment,
    likeComment,
  } = useEventComments();

  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    fetchComments(eventId);
  }, [eventId, fetchComments]);

  return (
    <section className="event-comments">
      <h2>Comments ({totalCount})</h2>

      {!showForm && (
        <button onClick={() => setShowForm(true)}>
          Add Your Comment
        </button>
      )}

      {showForm && (
        <EventCommentForm
          eventId={eventId}
          onSuccess={() => {
            setShowForm(false);
            fetchComments(eventId);
          }}
        />
      )}

      {rateLimitStatus && (
        <div className="rate-limit-indicator">
          <div className="progress-bar">
            <div
              style={{
                width: `${
                  (rateLimitStatus.comments_this_minute /
                    rateLimitStatus.limit_per_minute) *
                  100
                }%`,
              }}
            />
          </div>
          <p>
            {rateLimitStatus.comments_this_minute}/
            {rateLimitStatus.limit_per_minute} comments posted
          </p>
        </div>
      )}

      <div className="comments-list">
        {isLoading ? (
          <p>Loading comments...</p>
        ) : comments.length === 0 ? (
          <p>No comments yet. Be the first to comment!</p>
        ) : (
          comments.map((comment) => (
            <CommentCard
              key={comment.comment_id}
              comment={comment}
              onLike={() => likeComment(comment.comment_id)}
              onDelete={() => deleteComment(comment.comment_id)}
            />
          ))
        )}
      </div>
    </section>
  );
}
```

---

## Testing

### Test Comment Posting

```bash
curl -X POST http://localhost:5000/api/scraper/comments \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test_event_123",
    "author_name": "Test User",
    "author_email": "test@example.com",
    "text": "This is a test comment with at least 10 characters!"
  }'
```

### Test Comment Fetching

```bash
curl "http://localhost:5000/api/scraper/comments/test_event_123?limit=10"
```

### Test Rate Limiting

```bash
# Quick spam test
for i in {1..5}; do
  curl -X POST http://localhost:5000/api/scraper/comments \
    -H "Content-Type: application/json" \
    -d "{\"event_id\":\"test\",\"author_name\":\"spam\",\"text\":\"spam comment $i\"}"
  sleep 0.1
done
# Should get rate limited on 4th or 5th request
```

---

## FAQ

**Q: How are comments moderated?**
A: By default, auto-approved. Disable in code to require manual approval.

**Q: Can users edit their comments?**
A: Not currently, but can be added by implementing UPDATE endpoint.

**Q: How do I prevent spam?**
A: Rate limiting is built-in. Can also add CAPTCHA or email verification.

**Q: Can comments be deleted?**
A: Yes, soft deleted. Can restore by setting `is_deleted = false`.

**Q: Are comment emails stored publicly?**
A: No, only shown to authenticated admin users (if you implement that).

---

**Implementation Complete & Ready to Use** ✅
