#!/usr/bin/env python3
"""
Rate limiting middleware for API security
Prevents abuse and ensures fair usage
"""

import time
from functools import wraps
from typing import Optional, Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import os

# Try to import Redis, fallback to memory storage
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimiter:
    """Rate limiter with sliding window algorithm"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self._storage = {}  # Fallback storage if Redis unavailable
        self._redis = None
        
        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
                self._redis = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                print(f"[WARNING] Redis unavailable for rate limiting: {e}")
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique key for client (IP + endpoint)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        endpoint = request.url.path
        return f"rate_limit:{client_ip}:{endpoint}"
    
    async def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit
        
        Returns:
            (allowed, metadata) where metadata contains limit info
        """
        key = self._get_client_key(request)
        now = time.time()
        
        if self._redis:
            # Use Redis for distributed rate limiting
            pipe = self._redis.pipeline()

            # Remove old entries (sliding window)
            pipe.zremrangebyscore(key, 0, now - 3600)  # Keep last hour

            # Count requests in last minute
            pipe.zcount(key, now - 60, now)

            # Count requests in last hour
            pipe.zcount(key, now - 3600, now)

            results = await pipe.execute()
            minute_count = results[0]
            hour_count = results[1]
        else:
            # Use in-memory storage (per-instance only)
            if key not in self._storage:
                self._storage[key] = []

            # Clean old entries
            self._storage[key] = [
                ts for ts in self._storage[key]
                if ts > now - 3600
            ]

            # Count requests
            minute_count = sum(1 for ts in self._storage[key] if ts > now - 60)
            hour_count = len(self._storage[key])

        # Check limits BEFORE adding the current request
        allowed = (
            minute_count < self.requests_per_minute and
            hour_count < self.requests_per_hour
        )

        if allowed:
            # Only add the current request if it's allowed
            if self._redis:
                await self._redis.zadd(key, {str(now): now})
                await self._redis.expire(key, 3600)
            else:
                self._storage[key].append(now)
        
        # Calculate remaining limits (subtract 1 if the current request was allowed)
        minute_remaining = max(0, self.requests_per_minute - minute_count - (1 if allowed else 0))
        hour_remaining = max(0, self.requests_per_hour - hour_count - (1 if allowed else 0))

        metadata = {
            "limit_minute": self.requests_per_minute,
            "limit_hour": self.requests_per_hour,
            "remaining_minute": minute_remaining,
            "remaining_hour": hour_remaining,
            "reset_time": int(now + 60)
        }
        
        return allowed, metadata


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting
    Add to app: app.middleware("http")(rate_limit_middleware)
    """
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    allowed, metadata = await rate_limiter.is_allowed(request)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": 60,
                **metadata
            },
            headers={
                "X-RateLimit-Limit": str(metadata["limit_minute"]),
                "X-RateLimit-Remaining": str(metadata["remaining_minute"]),
                "X-RateLimit-Reset": str(metadata["reset_time"]),
                "Retry-After": "60"
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(metadata["limit_minute"])
    response.headers["X-RateLimit-Remaining"] = str(metadata["remaining_minute"])
    response.headers["X-RateLimit-Reset"] = str(metadata["reset_time"])
    
    return response


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000
):
    """
    Decorator for endpoint-specific rate limiting
    
    Example:
        @app.get("/api/events")
        @rate_limit(requests_per_minute=30)
        async def get_events():
            return {"events": []}
    """
    def decorator(func: Callable):
        limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour
        )
        
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            allowed, metadata = await limiter.is_allowed(request)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "retry_after": 60,
                        **metadata
                    }
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


class TokenBucketRateLimiter:
    """
    Token bucket algorithm for burst handling
    Good for endpoints that need to handle bursts of traffic
    """
    
    def __init__(
        self,
        capacity: int = 10,  # Maximum burst size
        refill_rate: float = 1.0  # Tokens per second
    ):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets = {}  # Client ID -> (tokens, last_update)
    
    def _get_tokens(self, client_id: str) -> float:
        """Get current token count for client"""
        now = time.time()
        
        if client_id not in self._buckets:
            self._buckets[client_id] = (self.capacity, now)
            return self.capacity
        
        tokens, last_update = self._buckets[client_id]
        
        # Refill tokens based on time elapsed
        elapsed = now - last_update
        new_tokens = min(
            self.capacity,
            tokens + (elapsed * self.refill_rate)
        )
        
        self._buckets[client_id] = (new_tokens, now)
        return new_tokens
    
    def consume(self, client_id: str, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket
        
        Returns:
            True if tokens were consumed, False otherwise
        """
        current_tokens = self._get_tokens(client_id)
        
        if current_tokens >= tokens:
            self._buckets[client_id] = (
                current_tokens - tokens,
                time.time()
            )
            return True
        
        return False


# IP whitelist/blacklist for additional security
class IPFilter:
    """Filter requests based on IP address"""
    
    def __init__(self):
        self.whitelist = set()
        self.blacklist = set()
        self._load_lists()
    
    def _load_lists(self):
        """Load IP lists from environment"""
        whitelist_str = os.environ.get('IP_WHITELIST', '')
        blacklist_str = os.environ.get('IP_BLACKLIST', '')
        
        if whitelist_str:
            self.whitelist = set(ip.strip() for ip in whitelist_str.split(','))
        
        if blacklist_str:
            self.blacklist = set(ip.strip() for ip in blacklist_str.split(','))
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if IP is allowed"""
        # If whitelist exists, only allow whitelisted IPs
        if self.whitelist and client_ip not in self.whitelist:
            return False
        
        # Check blacklist
        if client_ip in self.blacklist:
            return False
        
        return True


# Global IP filter
ip_filter = IPFilter()


async def ip_filter_middleware(request: Request, call_next):
    """Middleware to filter requests by IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    if not ip_filter.is_allowed(client_ip):
        return JSONResponse(
            status_code=403,
            content={"error": "Access denied"}
        )
    
    return await call_next(request)


if __name__ == "__main__":
    # Test rate limiter
    import asyncio
    
    async def test():
        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=100)
        
        # Mock request
        class MockClient:
            host = "127.0.0.1"
        
        class MockRequest:
            client = MockClient()
            url = type('URL', (), {'path': '/test'})()
            headers = {}
        
        request = MockRequest()
        
        # Test requests
        for i in range(7):
            allowed, metadata = await limiter.is_allowed(request)
            print(f"Request {i+1}: {'Allowed' if allowed else 'Denied'} - Remaining: {metadata['remaining_minute']}")
            await asyncio.sleep(0.1)
    
    asyncio.run(test())
