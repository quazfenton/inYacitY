"""
Comment system model and rate limiter
Handles event comments with anti-spam rate limiting
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class RateLimiter:
    """
    Simple in-memory rate limiter for comments
    
    Prevents spam by limiting:
    - Comments per IP/user per minute
    - Comments per IP/user per hour
    - Total comments per IP/user per day
    """
    
    def __init__(
        self,
        max_per_minute: int = 3,
        max_per_hour: int = 20,
        max_per_day: int = 100
    ):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        
        # Track comment timestamps by IP/user
        # Format: {ip_or_user: [timestamp1, timestamp2, ...]}
        self.comment_history: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user/IP is allowed to comment
        
        Args:
            identifier: IP address or user ID
        
        Returns:
            (is_allowed, reason_if_blocked)
        """
        now = time.time()
        
        # Clean old entries (older than 24 hours)
        cutoff_time = now - (86400)  # 24 hours in seconds
        self.comment_history[identifier] = [
            ts for ts in self.comment_history[identifier]
            if ts > cutoff_time
        ]
        
        timestamps = self.comment_history[identifier]
        
        # Check per-minute limit
        recent_minute = [
            ts for ts in timestamps
            if ts > (now - 60)  # Last 60 seconds
        ]
        if len(recent_minute) >= self.max_per_minute:
            wait_time = int(60 - (now - recent_minute[0])) + 1
            return False, f"Too many comments. Please wait {wait_time} seconds."
        
        # Check per-hour limit
        recent_hour = [
            ts for ts in timestamps
            if ts > (now - 3600)  # Last 3600 seconds (1 hour)
        ]
        if len(recent_hour) >= self.max_per_hour:
            wait_time = int(3600 - (now - recent_hour[0])) + 1
            return False, f"Hourly limit reached. Try again in {wait_time // 60} minutes."
        
        # Check per-day limit
        if len(timestamps) >= self.max_per_day:
            return False, "Daily comment limit reached. Come back tomorrow."
        
        return True, None
    
    def record_comment(self, identifier: str) -> None:
        """Record a comment for rate limiting"""
        self.comment_history[identifier].append(time.time())
    
    def get_stats(self, identifier: str) -> Dict:
        """Get rate limit stats for an identifier"""
        now = time.time()
        timestamps = self.comment_history.get(identifier, [])
        
        recent_minute = [ts for ts in timestamps if ts > (now - 60)]
        recent_hour = [ts for ts in timestamps if ts > (now - 3600)]
        
        return {
            'comments_this_minute': len(recent_minute),
            'comments_this_hour': len(recent_hour),
            'comments_today': len(timestamps),
            'limit_per_minute': self.max_per_minute,
            'limit_per_hour': self.max_per_hour,
            'limit_per_day': self.max_per_day,
        }


class CommentValidator:
    """Validate comment data"""
    
    MIN_LENGTH = 3
    MAX_LENGTH = 1000
    
    @staticmethod
    def validate(comment_text: str, author_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate comment content
        
        Returns:
            (is_valid, error_message)
        """
        if not comment_text or not comment_text.strip():
            return False, "Comment cannot be empty"
        
        comment_text = comment_text.strip()
        
        if len(comment_text) < CommentValidator.MIN_LENGTH:
            return False, f"Comment must be at least {CommentValidator.MIN_LENGTH} characters"
        
        if len(comment_text) > CommentValidator.MAX_LENGTH:
            return False, f"Comment must be under {CommentValidator.MAX_LENGTH} characters"
        
        if not author_name or not author_name.strip():
            return False, "Author name is required"
        
        author_name = author_name.strip()
        
        if len(author_name) > 255:
            return False, "Author name is too long"
        
        return True, None
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Basic sanitization of comment text"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Trim to max length just in case
        return text[:CommentValidator.MAX_LENGTH]


class Comment:
    """Comment data model"""
    
    def __init__(
        self,
        comment_id: str,
        event_id: str,
        author_name: str,
        author_email: Optional[str],
        text: str,
        created_at: str,
        updated_at: Optional[str] = None,
        likes: int = 0,
        is_approved: bool = True
    ):
        self.comment_id = comment_id
        self.event_id = event_id
        self.author_name = author_name
        self.author_email = author_email
        self.text = text
        self.created_at = created_at
        self.updated_at = updated_at
        self.likes = likes
        self.is_approved = is_approved
    
    def to_dict(self, include_email: bool = False) -> Dict:
        """Serialize comment to dictionary"""
        data = {
            'comment_id': self.comment_id,
            'event_id': self.event_id,
            'author_name': self.author_name,
            'text': self.text,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'likes': self.likes,
            'is_approved': self.is_approved,
        }
        
        if include_email and self.author_email:
            data['author_email'] = self.author_email
        
        return data
    
    @staticmethod
    def from_dict(data: Dict) -> 'Comment':
        """Deserialize comment from dictionary"""
        return Comment(
            comment_id=data['comment_id'],
            event_id=data['event_id'],
            author_name=data['author_name'],
            author_email=data.get('author_email'),
            text=data['text'],
            created_at=data['created_at'],
            updated_at=data.get('updated_at'),
            likes=data.get('likes', 0),
            is_approved=data.get('is_approved', True)
        )
