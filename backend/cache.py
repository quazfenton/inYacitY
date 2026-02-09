#!/usr/bin/env python3
"""
Redis caching utilities for API performance optimization
Provides caching decorators and helper functions
"""

import json
import pickle
import hashlib
from functools import wraps
from typing import Optional, Any, Callable
from datetime import datetime, timedelta
import os

# Redis connection
_redis_client = None

def get_redis_client():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            _redis_client = redis.from_url(redis_url, decode_responses=True)
        except ImportError:
            print("[WARNING] Redis not installed, caching disabled")
            return None
        except Exception as e:
            print(f"[WARNING] Failed to connect to Redis: {e}")
            return None
    return _redis_client


class CacheManager:
    """Manager for Redis caching operations"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.client = get_redis_client()
        self.default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"[CACHE ERROR] Failed to get {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        serialize: str = 'json'
    ) -> bool:
        """Set value in cache"""
        if not self.client:
            return False
        
        try:
            if serialize == 'json':
                value_str = json.dumps(value, default=str)
            else:
                value_str = pickle.dumps(value)
            
            ttl = ttl or self.default_ttl
            await self.client.setex(key, ttl, value_str)
            return True
        except Exception as e:
            print(f"[CACHE ERROR] Failed to set {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False
        
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            print(f"[CACHE ERROR] Failed to delete {key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self.client:
            return 0
        
        try:
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"[CACHE ERROR] Failed to invalidate pattern {pattern}: {e}")
            return 0
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_data = f"{prefix}:{str(args)}:{str(kwargs)}"
        return hashlib.md5(key_data.encode()).hexdigest()


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    invalidate_on: Optional[list] = None
):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Custom key prefix (default: function name)
        invalidate_on: List of event types that invalidate this cache
    
    Example:
        @cached(ttl=600, key_prefix="events")
        async def get_city_events(city_id: str):
            return await fetch_events(city_id)
    """
    def decorator(func: Callable) -> Callable:
        prefix = key_prefix or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                print(f"[CACHE HIT] {prefix}")
                return cached_value
            
            # Call function
            print(f"[CACHE MISS] {prefix}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                await cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, skip caching or implement sync Redis
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def invalidate_cache(pattern: str):
    """Invalidate cache by pattern"""
    async def _invalidate():
        return await cache_manager.invalidate_pattern(pattern)
    
    # Run in event loop if available
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_invalidate())
        else:
            loop.run_until_complete(_invalidate())
    except:
        pass


# Cache key generators for common operations
def get_city_events_key(city_id: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> str:
    """Generate cache key for city events"""
    return f"events:{city_id}:{date_from}:{date_to}"


def get_event_detail_key(event_id: int) -> str:
    """Generate cache key for event details"""
    return f"event:{event_id}"


def get_cities_key() -> str:
    """Generate cache key for cities list"""
    return "cities:all"


def get_subscribers_key(city_id: str) -> str:
    """Generate cache key for subscribers"""
    return f"subscribers:{city_id}"


# Smart cache invalidation helpers
async def invalidate_city_events(city_id: str):
    """Invalidate all cached events for a city"""
    await cache_manager.invalidate_pattern(f"events:{city_id}:*")


async def invalidate_event(event_id: int):
    """Invalidate specific event cache"""
    await cache_manager.delete(get_event_detail_key(event_id))


async def invalidate_all_cities():
    """Invalidate cities list cache"""
    await cache_manager.delete(get_cities_key())


# Import asyncio here to avoid issues
import asyncio


if __name__ == "__main__":
    # Test caching
    async def test():
        print("Testing Redis cache...")
        
        # Test set/get
        await cache_manager.set("test_key", {"message": "Hello"}, ttl=60)
        result = await cache_manager.get("test_key")
        print(f"Cached value: {result}")
        
        # Test decorator
        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int):
            await asyncio.sleep(1)  # Simulate slow operation
            return x * 2
        
        # First call (cache miss)
        start = datetime.now()
        result1 = await expensive_function(5)
        duration1 = (datetime.now() - start).total_seconds()
        print(f"First call: {result1} (took {duration1:.2f}s)")
        
        # Second call (cache hit)
        start = datetime.now()
        result2 = await expensive_function(5)
        duration2 = (datetime.now() - start).total_seconds()
        print(f"Second call: {result2} (took {duration2:.2f}s)")
        
        print("Test complete!")
    
    asyncio.run(test())
