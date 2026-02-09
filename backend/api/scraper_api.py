"""
Flask Blueprint for scraper integration API
Handles:
- Email subscription management
- Database sync triggering
- Event RSVP and calendar integration
- Event data endpoints for frontend
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import os
import sys
import asyncio
import uuid
from urllib.parse import urlencode

# Add scraper directory to path
scraper_dir = os.path.join(os.path.dirname(__file__), '../../scraper')
sys.path.insert(0, scraper_dir)

from db_sync_enhanced import DatabaseSyncManager, SupabaseSync

# Import comment system
sys.path.insert(0, os.path.dirname(__file__))
from backend.models.comments import RateLimiter, CommentValidator

scraper_api = Blueprint('scraper_api', __name__, url_prefix='/api/scraper')


class ScraperAPIManager:
    """Manages scraper API operations"""
    
    _instance = None
    _sync_manager = None
    _sync_client = None
    _rate_limiter = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScraperAPIManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._sync_manager is None:
            self._sync_manager = DatabaseSyncManager()
            self._sync_client = SupabaseSync()
            self._rate_limiter = RateLimiter(
                max_per_minute=3,
                max_per_hour=20,
                max_per_day=100
            )
    
    @property
    def sync_manager(self):
        return self._sync_manager
    
    @property
    def sync_client(self):
        return self._sync_client
    
    @property
    def rate_limiter(self):
        return self._rate_limiter


def get_manager() -> ScraperAPIManager:
    """Get singleton manager instance"""
    return ScraperAPIManager()


# ===== EMAIL SUBSCRIPTION ENDPOINTS =====

@scraper_api.route('/email-subscribe', methods=['POST'])
def email_subscribe():
    """
    Subscribe email to city event updates
    
    Request body:
    {
        "email": "user@example.com",
        "city": "ca--los-angeles"
    }
    
    Response:
    {
        "success": true,
        "message": "Subscription created...",
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        email = data.get('email', '').strip()
        city = data.get('city', '').strip()
        
        # Validation
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        if not city:
            return jsonify({
                'success': False,
                'message': 'City is required'
            }), 400
        
        # Use async function
        manager = get_manager()
        
        # Create event loop and run sync function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(
                manager.sync_client.insert_email_subscription(email, city)
            )
        finally:
            loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@scraper_api.route('/email-unsubscribe', methods=['POST'])
def email_unsubscribe():
    """
    Unsubscribe email from city or all cities
    
    Request body:
    {
        "email": "user@example.com",
        "city": "ca--los-angeles"  (optional, omit to unsubscribe from all)
    }
    
    Response:
    {
        "success": true,
        "message": "Unsubscribed...",
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        email = data.get('email', '').strip()
        city = data.get('city')  # Optional
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        manager = get_manager()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(
                manager.sync_client.unsubscribe_email(email, city)
            )
        finally:
            loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


# ===== DATABASE SYNC ENDPOINTS =====

@scraper_api.route('/sync', methods=['POST'])
def trigger_sync():
    """
    Manually trigger database sync
    
    Optional body:
    {
        "force": false  (force sync regardless of config)
    }
    
    Response:
    {
        "success": true,
        "events_synced": 42,
        "new_duplicates_removed": 3,
        "past_events_removed": 5,
        "errors": [],
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        data = request.get_json() or {}
        force = data.get('force', False)
        
        manager = get_manager()
        
        # Run sync
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                manager.sync_manager.sync_events()
            )
        finally:
            loop.close()
        
        return jsonify({
            'success': result['success'],
            'events_synced': result['events_synced'],
            'new_duplicates_removed': result['new_duplicates_removed'],
            'past_events_removed': result['past_events_removed'],
            'errors': result['errors'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200 if result['success'] else 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Sync error: {str(e)}',
            'errors': [str(e)],
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@scraper_api.route('/sync-status', methods=['GET'])
def sync_status():
    """
    Get database sync status and deduplication stats
    
    Response:
    {
        "configured": true,
        "dedup_stats": {
            "total_tracked": 1000,
            "last_updated": "2026-02-06T12:00:00..."
        },
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        manager = get_manager()
        
        return jsonify({
            'configured': manager.sync_client.is_configured(),
            'dedup_stats': manager.sync_manager.get_dedup_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving status: {str(e)}'
        }), 500


# ===== HEALTH CHECK =====

@scraper_api.route('/health', methods=['GET'])
def health():
    """
    Check scraper API health
    
    Response:
    {
        "status": "healthy",
        "supabase_configured": true,
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        manager = get_manager()
        
        return jsonify({
            'status': 'healthy',
            'supabase_configured': manager.sync_client.is_configured(),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ===== RSVP & CALENDAR ENDPOINTS =====

@scraper_api.route('/rsvp', methods=['POST'])
def rsvp_event():
    """
    RSVP to an event with optional calendar integration
    
    Request body:
    {
        "event_id": "event_hash_or_id",
        "title": "Event Title",
        "date": "2026-02-15",
        "time": "7:00 PM",
        "location": "Los Angeles, CA",
        "description": "Event description",
        "user_name": "John Doe",
        "user_email": "user@example.com",
        "calendar_type": "google" | "apple" | null,
        "reminder_enabled": true,
        "reminder_minutes": 120
    }
    
    Response:
    {
        "success": true,
        "rsvp_id": "uuid",
        "calendar_url": "https://calendar.google.com/...",
        "message": "RSVP recorded",
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validation
        required_fields = ['event_id', 'title', 'date', 'location']
        missing = [f for f in required_fields if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        event_id = str(data.get('event_id')).strip()
        title = str(data.get('title')).strip()
        date_str = str(data.get('date')).strip()
        time_str = str(data.get('time', 'TBA')).strip()
        location = str(data.get('location')).strip()
        description = str(data.get('description', '')).strip()
        user_name = str(data.get('user_name', 'Guest')).strip()
        user_email = str(data.get('user_email', '')).strip()
        calendar_type = str(data.get('calendar_type', '')).lower() or None
        reminder_enabled = data.get('reminder_enabled', False)
        reminder_minutes = data.get('reminder_minutes', 120)
        
        # Validate calendar type
        if calendar_type and calendar_type not in ['google', 'apple']:
            return jsonify({
                'success': False,
                'message': 'Invalid calendar type. Must be "google", "apple", or null'
            }), 400
        
        # Generate RSVP ID
        rsvp_id = str(uuid.uuid4())
        
        # Create calendar URL if calendar type specified
        calendar_url = None
        if calendar_type == 'google':
            calendar_url = _generate_google_calendar_url(
                title, date_str, time_str, location, description, reminder_minutes
            )
        elif calendar_type == 'apple':
            calendar_url = _generate_apple_calendar_url(
                title, date_str, time_str, location, description
            )
        
        # Record RSVP in database (if Supabase configured)
        manager = get_manager()
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                # Insert RSVP record
                client.table('rsvps').insert({
                    'rsvp_id': rsvp_id,
                    'event_id': event_id,
                    'event_title': title,
                    'event_date': date_str,
                    'event_time': time_str,
                    'user_name': user_name,
                    'user_email': user_email,
                    'calendar_type': calendar_type,
                    'reminder_enabled': reminder_enabled,
                    'reminder_minutes': reminder_minutes,
                    'created_at': datetime.utcnow().isoformat()
                }).execute()
            except Exception as e:
                print(f"Warning: Could not record RSVP: {e}")
                # Continue anyway - RSVP still works, just not tracked
        
        return jsonify({
            'success': True,
            'rsvp_id': rsvp_id,
            'calendar_url': calendar_url,
            'message': f'RSVP recorded for {user_name}',
            'reminder_enabled': reminder_enabled,
            'timestamp': datetime.utcnow().isoformat()
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@scraper_api.route('/rsvp/<rsvp_id>', methods=['DELETE'])
def cancel_rsvp(rsvp_id):
    """
    Cancel an RSVP
    
    Response:
    {
        "success": true,
        "message": "RSVP cancelled",
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        manager = get_manager()
        
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                # Delete RSVP record
                client.table('rsvps')\
                    .delete()\
                    .eq('rsvp_id', rsvp_id)\
                    .execute()
            except Exception as e:
                print(f"Warning: Could not delete RSVP: {e}")
        
        return jsonify({
            'success': True,
            'message': 'RSVP cancelled',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@scraper_api.route('/rsvp-status/<event_id>', methods=['GET'])
def rsvp_status(event_id):
    """
    Get RSVP count and attendee list for an event
    
    Response:
    {
        "success": true,
        "event_id": "event_hash",
        "rsvp_count": 42,
        "attendees": [
            {"name": "John Doe", "email": "john@example.com", "rsvp_id": "uuid"},
            ...
        ],
        "timestamp": "2026-02-06T12:34:56..."
    }
    """
    try:
        manager = get_manager()
        rsvp_count = 0
        attendees = []
        
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                response = client.table('rsvps')\
                    .select('rsvp_id, user_name, user_email')\
                    .eq('event_id', event_id)\
                    .execute()
                
                if response.data:
                    attendees = response.data
                    rsvp_count = len(attendees)
            except Exception as e:
                print(f"Warning: Could not fetch RSVP status: {e}")
        
        return jsonify({
            'success': True,
            'event_id': event_id,
            'rsvp_count': rsvp_count,
            'attendees': attendees,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


# ===== COMMENTS ENDPOINTS =====

@scraper_api.route('/comments/<event_id>', methods=['GET'])
def get_comments(event_id):
    """
    Get all comments for an event
    
    Query params:
      - approved: "true" to only show approved comments (default: true)
      - limit: number of comments to return (default: 50)
      - offset: pagination offset (default: 0)
    
    Response:
    {
        "success": true,
        "event_id": "event_hash",
        "comments": [
            {
                "comment_id": "uuid",
                "author_name": "John Doe",
                "text": "Great event!",
                "created_at": "2026-02-06T12:34:56Z",
                "likes": 5,
                "is_approved": true
            }
        ],
        "total_count": 42,
        "timestamp": "2026-02-06T12:34:56Z"
    }
    """
    try:
        # Params
        approved_only = request.args.get('approved', 'true').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 500)  # Max 500
        offset = int(request.args.get('offset', 0))
        
        manager = get_manager()
        comments = []
        total_count = 0
        
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                # Build query
                query = client.table('comments')\
                    .select('comment_id, author_name, text, created_at, updated_at, likes, is_approved')\
                    .eq('event_id', event_id)\
                    .eq('is_deleted', False)\
                    .order('created_at', desc=True)
                
                if approved_only:
                    query = query.eq('is_approved', True)
                
                # Get total count
                count_response = client.table('comments')\
                    .select('count', count='exact')\
                    .eq('event_id', event_id)\
                    .eq('is_deleted', False)
                
                if approved_only:
                    count_response = count_response.eq('is_approved', True)
                
                count_data = count_response.execute()
                total_count = count_data.count if hasattr(count_data, 'count') else 0
                
                # Get paginated results
                response = query.range(offset, offset + limit - 1).execute()
                comments = response.data if response.data else []
            except Exception as e:
                print(f"Warning: Could not fetch comments: {e}")
        
        return jsonify({
            'success': True,
            'event_id': event_id,
            'comments': comments,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching comments: {str(e)}'
        }), 500


@scraper_api.route('/comments', methods=['POST'])
def post_comment():
    """
    Post a comment on an event
    
    Request body:
    {
        "event_id": "event_hash",
        "author_name": "John Doe",
        "author_email": "john@example.com",
        "text": "This event was amazing!"
    }
    
    Rate limiting:
      - 3 comments per minute per IP
      - 20 comments per hour per IP
      - 100 comments per day per IP
    
    Response:
    {
        "success": true,
        "comment_id": "uuid",
        "message": "Comment posted successfully",
        "is_approved": true,
        "timestamp": "2026-02-06T12:34:56Z"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Get client identifier (IP address)
        client_ip = request.remote_addr or 'unknown'
        
        # Validate data
        event_id = str(data.get('event_id', '')).strip()
        author_name = str(data.get('author_name', '')).strip()
        author_email = str(data.get('author_email', '')).strip() or None
        text = str(data.get('text', '')).strip()
        
        if not event_id:
            return jsonify({
                'success': False,
                'message': 'Event ID is required'
            }), 400
        
        # Validate comment content
        is_valid, error = CommentValidator.validate(text, author_name)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        # Check rate limiting
        manager = get_manager()
        is_allowed, rate_error = manager.rate_limiter.is_allowed(client_ip)
        if not is_allowed:
            return jsonify({
                'success': False,
                'message': rate_error,
                'rate_limited': True
            }), 429  # Too Many Requests
        
        # Record comment for rate limiting
        manager.rate_limiter.record_comment(client_ip)
        
        # Sanitize comment
        text = CommentValidator.sanitize(text)
        
        # Generate comment ID
        comment_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Insert comment in database
        is_approved = True  # Can be changed to False for moderation
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                client.table('comments').insert({
                    'comment_id': comment_id,
                    'event_id': event_id,
                    'author_name': author_name,
                    'author_email': author_email,
                    'author_ip': client_ip,
                    'text': text,
                    'is_approved': is_approved,
                    'created_at': now,
                    'updated_at': now
                }).execute()
            except Exception as e:
                print(f"Warning: Could not save comment: {e}")
        
        return jsonify({
            'success': True,
            'comment_id': comment_id,
            'message': 'Comment posted successfully',
            'is_approved': is_approved,
            'timestamp': now
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error posting comment: {str(e)}'
        }), 500


@scraper_api.route('/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """
    Delete a comment (soft delete - marks as deleted)
    
    Response:
    {
        "success": true,
        "message": "Comment deleted",
        "timestamp": "2026-02-06T12:34:56Z"
    }
    """
    try:
        manager = get_manager()
        
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                # Soft delete
                client.table('comments')\
                    .update({'is_deleted': True, 'updated_at': datetime.utcnow().isoformat()})\
                    .eq('comment_id', comment_id)\
                    .execute()
            except Exception as e:
                print(f"Warning: Could not delete comment: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Comment deleted',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting comment: {str(e)}'
        }), 500


@scraper_api.route('/comments/<comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    """
    Like a comment (increment likes counter)
    
    Response:
    {
        "success": true,
        "comment_id": "uuid",
        "likes": 6,
        "timestamp": "2026-02-06T12:34:56Z"
    }
    """
    try:
        manager = get_manager()
        
        if manager.sync_client.is_configured():
            try:
                from supabase import create_client
                client = create_client(
                    os.environ.get('SUPABASE_URL'),
                    os.environ.get('SUPABASE_KEY')
                )
                
                # Get current likes
                response = client.table('comments')\
                    .select('likes')\
                    .eq('comment_id', comment_id)\
                    .single()\
                    .execute()
                
                current_likes = response.data.get('likes', 0) if response.data else 0
                new_likes = current_likes + 1
                
                # Update likes
                client.table('comments')\
                    .update({'likes': new_likes, 'updated_at': datetime.utcnow().isoformat()})\
                    .eq('comment_id', comment_id)\
                    .execute()
                
                return jsonify({
                    'success': True,
                    'comment_id': comment_id,
                    'likes': new_likes,
                    'timestamp': datetime.utcnow().isoformat()
                }), 200
            except Exception as e:
                print(f"Warning: Could not like comment: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Error liking comment: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'Database not configured'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error liking comment: {str(e)}'
        }), 500


@scraper_api.route('/comments/rate-limit/status', methods=['GET'])
def rate_limit_status():
    """
    Get current rate limit status for client IP
    
    Response:
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
        "timestamp": "2026-02-06T12:34:56Z"
    }
    """
    try:
        client_ip = request.remote_addr or 'unknown'
        manager = get_manager()
        
        stats = manager.rate_limiter.get_stats(client_ip)
        
        return jsonify({
            'success': True,
            'rate_limit': stats,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error checking rate limit: {str(e)}'
        }), 500


# ===== CALENDAR HELPER FUNCTIONS =====

def _generate_google_calendar_url(title, date_str, time_str, location, description, reminder_minutes=120):
    """
    Generate Google Calendar URL for adding event
    Format: https://calendar.google.com/calendar/render?action=TEMPLATE&...
    """
    try:
        # Parse date and time
        event_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Try to parse time, default to 00:00 if "TBA"
        if time_str and time_str.upper() != 'TBA':
            try:
                time_obj = datetime.strptime(time_str, '%I:%M %p')
                event_date = event_date.replace(hour=time_obj.hour, minute=time_obj.minute)
            except:
                # If parsing fails, just use date with 00:00
                pass
        
        # Generate end time (assume 2 hours)
        end_date = event_date + timedelta(hours=2)
        
        # Format for Google Calendar (RFC 3339: YYYYMMDDTHHMMSS)
        start_time = event_date.strftime('%Y%m%dT%H%M%S')
        end_time = end_date.strftime('%Y%m%dT%H%M%S')
        
        # Build params
        params = {
            'action': 'TEMPLATE',
            'text': title,
            'dates': f'{start_time}/{end_time}',
            'location': location,
            'details': description
        }
        
        url = f"https://calendar.google.com/calendar/render?{urlencode(params)}"
        return url
    except Exception as e:
        print(f"Error generating Google Calendar URL: {e}")
        return None


def _generate_apple_calendar_url(title, date_str, time_str, location, description):
    """
    Generate Apple Calendar URL for adding event
    Format: webcal://... (uses calendar:// for modern Apple Calendar)
    """
    try:
        # Parse date and time
        event_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Try to parse time, default to 00:00 if "TBA"
        if time_str and time_str.upper() != 'TBA':
            try:
                time_obj = datetime.strptime(time_str, '%I:%M %p')
                event_date = event_date.replace(hour=time_obj.hour, minute=time_obj.minute)
            except:
                pass
        
        # Generate end time (assume 2 hours)
        end_date = event_date + timedelta(hours=2)
        
        # Format for iCal
        start_time = event_date.strftime('%Y%m%dT%H%M%S')
        end_time = end_date.strftime('%Y%m%dT%H%M%S')
        
        # Build iCal URL (simple format)
        params = {
            'title': title,
            'dates': f'{start_time}/{end_time}',
            'location': location,
            'description': description
        }
        
        # Apple Calendar URL format
        url = f"webcal://calendar.apple.com/?{urlencode(params)}"
        return url
    except Exception as e:
        print(f"Error generating Apple Calendar URL: {e}")
        return None


# ===== ERROR HANDLERS =====

@scraper_api.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'message': 'Bad request',
        'error': str(error)
    }), 400


@scraper_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404


@scraper_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error',
        'error': str(error)
    }), 500
