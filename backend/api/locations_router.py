"""
Location API Endpoints for FastAPI

RESTful API for:
- Geolocation detection
- City discovery
- Proximity-based queries
- User location preferences
- Event filtering by location
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import math

from backend.models.locations import (
    Coordinates, Location, LocationPreference, LocationDatabase,
    LocationTier
)

# Initialize location database (singleton)
location_db = LocationDatabase()

# Create Router
router = APIRouter(prefix="/api/locations", tags=["locations"])


# ============================================================================
# Pydantic Models
# ============================================================================

class CoordinatesRequest(BaseModel):
    latitude: float
    longitude: float

class NearestCitiesRequest(BaseModel):
    latitude: float
    longitude: float
    limit: int = 5

class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius_miles: float = 25.0
    tier: Optional[str] = None

class LocationPreferenceRequest(BaseModel):
    user_id: str
    major_city_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    auto_detect: bool = True
    preferred_radius: float = 25.0


# ============================================================================
# DISCOVERY ENDPOINTS
# ============================================================================

@router.get("/major-cities")
async def get_major_cities(
    sort_by: str = Query("name", description="Sort by: name, population, or distance_from"),
    country: Optional[str] = Query(None, description="Filter by country code"),
    lat: Optional[float] = Query(None, description="Latitude for distance sorting"),
    lon: Optional[float] = Query(None, description="Longitude for distance sorting"),
    limit: int = Query(50, description="Maximum results to return")
):
    """
    Get all major cities with optional filtering and sorting
    """
    try:
        major_cities = location_db.get_major_cities()
        
        # Filter by country if specified
        if country:
            major_cities = [c for c in major_cities if c.country == country.upper()]
        
        # Sort options
        if sort_by == "population":
            major_cities = sorted(major_cities, key=lambda x: x.population or 0, reverse=True)
        elif sort_by == "distance_from":
            # Calculate distance from provided coordinates
            if lat is not None and lon is not None:
                user_coords = Coordinates(lat, lon)
                major_cities = sorted(
                    major_cities,
                    key=lambda x: user_coords.distance_to(x.coordinates)
                )
        
        # Limit results
        major_cities = major_cities[:limit]
        
        return {
            "success": True,
            "count": len(major_cities),
            "cities": [city.to_dict() for city in major_cities]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/location/{code}")
async def get_location(code: str):
    """
    Get location details by code
    """
    try:
        location = location_db.get_location(code)
        
        if not location:
            raise HTTPException(status_code=404, detail=f"Location {code} not found")
        
        # Get secondary cities if this is a major city
        secondary_cities = []
        if location.tier == LocationTier.MAJOR_CITY:
            secondary_cities = [
                loc.to_dict() for loc in location_db.locations.values()
                if loc.parent_city == code
            ]
        
        return {
            "success": True,
            "location": location.to_dict(),
            "secondary_cities": secondary_cities
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# GEOLOCATION ENDPOINTS
# ============================================================================

@router.post("/nearest-cities")
async def find_nearest_cities(request: NearestCitiesRequest):
    """
    Find nearest major cities to given coordinates
    """
    try:
        user_coords = Coordinates(request.latitude, request.longitude)
        nearest = location_db.find_nearest_city(user_coords, limit=request.limit)
        
        return {
            "success": True,
            "center": {
                "latitude": request.latitude,
                "longitude": request.longitude
            },
            "results": [
                {
                    "location": loc.to_dict(),
                    "distance_miles": round(distance, 2)
                }
                for loc, distance in nearest
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nearby")
async def get_nearby_locations(request: NearbyRequest):
    """
    Get all locations within specified radius
    """
    try:
        user_coords = Coordinates(request.latitude, request.longitude)
        nearby = location_db.get_nearby_locations(user_coords, request.radius_miles)
        
        # Filter by tier if specified
        if request.tier:
            nearby = [(loc, dist) for loc, dist in nearby if loc.tier.value == request.tier]
        
        return {
            "success": True,
            "center": {
                "latitude": request.latitude,
                "longitude": request.longitude
            },
            "radius_miles": request.radius_miles,
            "count": len(nearby),
            "results": [
                {
                    "location": loc.to_dict(),
                    "distance_miles": round(distance, 2)
                }
                for loc, distance in nearby
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# USER PREFERENCE ENDPOINTS
# ============================================================================

# In-memory storage for preferences (replace with database in production)
_user_preferences = {}

@router.post("/preferences")
async def save_location_preference(request: LocationPreferenceRequest):
    """
    Save user's location preference
    """
    try:
        # Create preference object
        secondary_coords = None
        if request.latitude and request.longitude:
            secondary_coords = Coordinates(request.latitude, request.longitude)
        
        preference = LocationPreference(
            user_id=request.user_id,
            major_city_code=request.major_city_code,
            secondary_location=secondary_coords,
            auto_detect=request.auto_detect,
            preferred_radius=request.preferred_radius
        )
        
        # Store preference (in production, save to database)
        _user_preferences[request.user_id] = preference
        
        return {
            "success": True,
            "message": "Location preference saved",
            "preference": preference.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/preferences/{user_id}")
async def get_location_preference(user_id: str):
    """
    Get user's saved location preference
    """
    try:
        preference = _user_preferences.get(user_id)
        
        if not preference:
            raise HTTPException(status_code=404, detail="No preference found for user")
        
        return {
            "success": True,
            "preference": preference.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@router.get("/search")
async def search_locations(
    q: str = Query(..., min_length=2, description="Search query"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    country: Optional[str] = Query(None, description="Filter by country"),
    limit: int = Query(20, description="Maximum results")
):
    """
    Search locations by name or code
    """
    try:
        query_lower = q.lower()
        results = []
        
        for loc in location_db.locations.values():
            # Search in name and code
            if (query_lower in loc.name.lower() or 
                query_lower in loc.code.lower()):
                
                # Apply filters
                if tier and loc.tier.value != tier:
                    continue
                if country and loc.country != country.upper():
                    continue
                
                results.append(loc)
        
        # Sort by relevance (exact match first)
        results.sort(key=lambda x: (
            0 if query_lower == x.code.lower() else
            1 if query_lower == x.name.lower() else
            2
        ))
        
        # Limit results
        results = results[:limit]
        
        return {
            "success": True,
            "query": q,
            "count": len(results),
            "results": [loc.to_dict() for loc in results]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# EVENTS BY LOCATION
# ============================================================================

@router.get("/events/nearby")
async def get_events_nearby(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius_miles: float = Query(25.0, description="Radius in miles"),
    limit: int = Query(100, description="Maximum events to return")
):
    """
    Get events within specified radius of coordinates
    Requires database integration
    """
    try:
        from backend.database import AsyncSessionLocal, Event
        from sqlalchemy import select, and_
        from datetime import date
        
        user_coords = Coordinates(lat, lon)
        today = date.today()
        
        async with AsyncSessionLocal() as db:
            # Get future events only (already sorted by date from database)
            result = await db.execute(
                select(Event)
                .where(Event.date >= today)
                .order_by(Event.date, Event.time)
                .limit(limit)
            )
            events = result.scalars().all()
            
            # Calculate distance for each event and filter
            nearby_events = []
            for event in events:
                # Get coordinates for event's city
                city_location = location_db.get_location(event.city_id)
                if city_location:
                    distance = user_coords.distance_to(city_location.coordinates)
                    if distance <= radius_miles:
                        nearby_events.append({
                            "id": event.id,
                            "title": event.title,
                            "date": event.date.isoformat() if event.date else None,
                            "time": event.time,
                            "location": event.location,
                            "city_id": event.city_id,
                            "distance_miles": round(distance, 2)
                        })
            
            # Sort by distance (required for this endpoint as it's the main criteria)
            nearby_events.sort(key=lambda x: x["distance_miles"])
            
            return {
                "success": True,
                "center": {"latitude": lat, "longitude": lon},
                "radius_miles": radius_miles,
                "count": len(nearby_events),
                "events": nearby_events
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events/by-city/{city_code}")
async def get_events_by_city(
    city_code: str,
    include_nearby: bool = Query(False, description="Include events from nearby cities"),
    radius_miles: float = Query(25.0, description="Radius for nearby cities")
):
    """
    Get events for a specific city, optionally including nearby cities
    """
    try:
        from backend.database import AsyncSessionLocal, Event
        from sqlalchemy import select
        
        # Get city location
        city_location = location_db.get_location(city_code)
        if not city_location:
            raise HTTPException(status_code=404, detail=f"City {city_code} not found")
        
        async with AsyncSessionLocal() as db:
            if include_nearby:
                # Get nearby cities
                nearby = location_db.get_nearby_locations(
                    city_location.coordinates, 
                    radius_miles
                )
                city_codes = [city_code] + [loc.code for loc, _ in nearby]
                
                # Query events for all nearby cities
                result = await db.execute(
                    select(Event).where(Event.city_id.in_(city_codes))
                )
            else:
                # Query events for specific city only
                result = await db.execute(
                    select(Event).where(Event.city_id == city_code)
                )
            
            events = result.scalars().all()
            
            return {
                "success": True,
                "city": city_code,
                "include_nearby": include_nearby,
                "radius_miles": radius_miles if include_nearby else None,
                "count": len(events),
                "events": [
                    {
                        "id": event.id,
                        "title": event.title,
                        "date": event.date.isoformat() if event.date else None,
                        "time": event.time,
                        "location": event.location,
                        "city_id": event.city_id
                    }
                    for event in events
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# STATS & HEALTH
# ============================================================================

@router.get("/stats")
async def get_stats():
    """
    Get location database statistics
    """
    try:
        locations = list(location_db.locations.values())
        
        return {
            "success": True,
            "stats": {
                "total_locations": len(locations),
                "countries": len(set(loc.country for loc in locations)),
                "by_tier": {
                    "major": len([l for l in locations if l.tier == LocationTier.MAJOR_CITY]),
                    "secondary": len([l for l in locations if l.tier == LocationTier.SECONDARY_CITY]),
                    "town": len([l for l in locations if l.tier == LocationTier.TOWN]),
                    "region": len([l for l in locations if l.tier == LocationTier.REGION])
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database_loaded": len(location_db.locations) > 0
    }
