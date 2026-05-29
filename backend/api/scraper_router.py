from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
from urllib.parse import urlencode

from models.comments import RateLimiter, CommentValidator, Comment as CommentModel

router = APIRouter(prefix="/api/scraper")

# In-memory storage
rsvps: dict = {}
comments_store: dict = {}
rate_limiter = RateLimiter(max_per_minute=3, max_per_hour=20, max_per_day=100)


# ── RSVP ─────────────────────────────────────────────────────────────────

class RSVPCreate(BaseModel):
    event_id: str
    title: str
    date: str
    time: Optional[str] = "TBA"
    location: str
    description: Optional[str] = ""
    user_name: str
    user_email: Optional[str] = ""
    calendar_type: Optional[str] = None
    reminder_enabled: Optional[bool] = False
    reminder_minutes: Optional[int] = 120


@router.post("/rsvp")
async def rsvp_event(data: RSVPCreate):
    rsvp_id = str(uuid.uuid4())
    calendar_url = None

    if data.calendar_type == "google":
        calendar_url = _google_calendar_url(data.title, data.date, data.time, data.location, data.description, data.reminder_minutes)
    elif data.calendar_type == "apple":
        calendar_url = _apple_calendar_url(data.title, data.date, data.time, data.location, data.description)

    rsvps[rsvp_id] = {
        "rsvp_id": rsvp_id,
        "event_id": data.event_id,
        "user_name": data.user_name,
        "user_email": data.user_email,
        "created_at": datetime.utcnow().isoformat(),
    }

    return {
        "success": True,
        "rsvp_id": rsvp_id,
        "calendar_url": calendar_url,
        "message": f"RSVP recorded for {data.user_name}",
        "reminder_enabled": data.reminder_enabled,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.delete("/rsvp/{rsvp_id}")
async def cancel_rsvp(rsvp_id: str):
    rsvps.pop(rsvp_id, None)
    return {
        "success": True,
        "message": "RSVP cancelled",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/rsvp-status/{event_id}")
async def rsvp_status(event_id: str):
    attendees = [r for r in rsvps.values() if r["event_id"] == event_id]
    return {
        "success": True,
        "event_id": event_id,
        "rsvp_count": len(attendees),
        "attendees": attendees,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── COMMENTS ─────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    event_id: str
    author_name: str
    author_email: Optional[str] = ""
    text: str


@router.get("/comments/{event_id}")
async def get_comments(event_id: str, approved: bool = True, limit: int = 50, offset: int = 0):
    all_comments = [c for c in comments_store.values() if c["event_id"] == event_id and not c.get("is_deleted")]
    if approved:
        all_comments = [c for c in all_comments if c["is_approved"]]
    total = len(all_comments)
    page = all_comments[offset:offset + limit]
    return {
        "success": True,
        "event_id": event_id,
        "comments": page,
        "total_count": total,
        "limit": limit,
        "offset": offset,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/comments")
async def post_comment(data: CommentCreate, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    is_valid, error = CommentValidator.validate(data.text, data.author_name)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    is_allowed, rate_error = rate_limiter.is_allowed(client_ip)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=rate_error)

    rate_limiter.record_comment(client_ip)

    comment_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    comments_store[comment_id] = {
        "comment_id": comment_id,
        "event_id": data.event_id,
        "author_name": data.author_name,
        "author_email": data.author_email,
        "text": CommentValidator.sanitize(data.text),
        "created_at": now,
        "updated_at": now,
        "likes": 0,
        "is_approved": True,
        "is_deleted": False,
    }

    return {
        "success": True,
        "comment_id": comment_id,
        "message": "Comment posted successfully",
        "is_approved": True,
        "timestamp": now,
    }


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str):
    if comment_id in comments_store:
        comments_store[comment_id]["is_deleted"] = True
        comments_store[comment_id]["updated_at"] = datetime.utcnow().isoformat()
    return {
        "success": True,
        "message": "Comment deleted",
    }


@router.post("/comments/{comment_id}/like")
async def like_comment(comment_id: str):
    if comment_id not in comments_store:
        raise HTTPException(status_code=404, detail="Comment not found")
    comments_store[comment_id]["likes"] += 1
    comments_store[comment_id]["updated_at"] = datetime.utcnow().isoformat()
    return {
        "success": True,
        "comment_id": comment_id,
        "likes": comments_store[comment_id]["likes"],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/comments/rate-limit/status")
async def rate_limit_status(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    stats = rate_limiter.get_stats(client_ip)
    return {
        "success": True,
        "rate_limit": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── CALENDAR HELPERS ─────────────────────────────────────────────────────

def _google_calendar_url(title: str, date_str: str, time_str: str, location: str, description: str, reminder_minutes: int = 120) -> Optional[str]:
    try:
        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        if time_str and time_str.upper() != "TBA":
            try:
                time_obj = datetime.strptime(time_str, "%I:%M %p")
                event_date = event_date.replace(hour=time_obj.hour, minute=time_obj.minute)
            except ValueError:
                pass
        end_date = event_date + timedelta(hours=2)
        start_fmt = event_date.strftime("%Y%m%dT%H%M%S")
        end_fmt = end_date.strftime("%Y%m%dT%H%M%S")
        params = {"action": "TEMPLATE", "text": title, "dates": f"{start_fmt}/{end_fmt}", "location": location, "details": description}
        return f"https://calendar.google.com/calendar/render?{urlencode(params)}"
    except Exception:
        return None


def _apple_calendar_url(title: str, date_str: str, time_str: str, location: str, description: str) -> Optional[str]:
    try:
        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        if time_str and time_str.upper() != "TBA":
            try:
                time_obj = datetime.strptime(time_str, "%I:%M %p")
                event_date = event_date.replace(hour=time_obj.hour, minute=time_obj.minute)
            except ValueError:
                pass
        end_date = event_date + timedelta(hours=2)
        start_fmt = event_date.strftime("%Y%m%dT%H%M%S")
        end_fmt = end_date.strftime("%Y%m%dT%H%M%S")
        params = {"title": title, "dates": f"{start_fmt}/{end_fmt}", "location": location, "description": description}
        return f"webcal://calendar.apple.com/?{urlencode(params)}"
    except Exception:
        return None
