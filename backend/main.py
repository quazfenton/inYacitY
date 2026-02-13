#!/usr/bin/env python3
"""
FastAPI Backend for Nocturne Event Platform
Integrates scraper functionality with database storage and API endpoints
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from datetime import datetime, date
import os
import sys
import asyncio
from contextlib import asynccontextmanager

# Add scraper to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../scraper'))

from database import (
    engine, Base, get_db, 
    Event, Subscription, init_db
)
from scraper_integration import scrape_city_events, refresh_all_cities

# Import authentication utilities
from auth import get_current_admin

# Pydantic models for API
class EventResponse(BaseModel):
    id: int
    title: str
    link: str
    date: date
    time: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    source: str
    city: str

    class Config:
        from_attributes = True

import re

class SubscriptionCreate(BaseModel):
    email: EmailStr
    city: str

    @validator('email')
    def validate_email_format(cls, v):
        # Additional validation beyond Pydantic's EmailStr
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower().strip()  # Normalize email

    @validator('city')
    def validate_city(cls, v):
        from config import CONFIG
        supported = CONFIG.get('SUPPORTED_LOCATIONS', [])
        if v not in supported:
            raise ValueError(f'City {v} not supported')
        return v

class SubscriptionResponse(BaseModel):
    id: int
    email: str
    city: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    total_events: int
    total_subscribers: int

# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    from database import init_db_async
    await init_db_async()
    yield
    # Shutdown: Close database connections
    from database import engine
    await engine.dispose()

# Create FastAPI app
app = FastAPI(
    title="Nocturne API",
    description="Backend API for underground event discovery platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check(db=Depends(get_db)):
    from sqlalchemy import func, select
    from database import Event, Subscription
    
    total_events = await db.scalar(select(func.count()).select_from(Event))
    total_subscribers = await db.scalar(select(func.count()).select_from(Subscription))
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        total_events=total_events or 0,
        total_subscribers=total_subscribers or 0
    )

# Get all supported cities
@app.get("/cities")
async def get_cities():
    """Get list of supported cities"""
    from config import CONFIG
    from scraper_integration import CITY_MAPPING
    
    cities = []
    supported = CONFIG.get('SUPPORTED_LOCATIONS', [])
    
    for city in supported:
        city_info = CITY_MAPPING.get(city, {
            'id': city,
            'name': city.replace('--', ' ').title(),
            'slug': city.replace('--', '-').lower()
        })
        city_info['id'] = city
        cities.append(city_info)
    
    return {"cities": cities}

# Get events for a specific city
@app.get("/events/{city}", response_model=List[EventResponse])
async def get_city_events(
    city: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    db=Depends(get_db)
):
    """Get events for a specific city with optional date filtering - Returns future events only by default"""
    from database import get_future_events_for_city

    # Validate city
    from config import CONFIG
    supported_locations = CONFIG.get('SUPPORTED_LOCATIONS', [])
    if city not in supported_locations:
        raise HTTPException(status_code=404, detail=f"City {city} not supported")

    # Use the database function that filters for future events
    events = await get_future_events_for_city(city, start_date, end_date, limit)
    return events

# Refresh all cities
@app.post("/scrape/all")
async def scrape_all(background_tasks: BackgroundTasks):
    """Trigger scraping for all supported cities"""
    background_tasks.add_task(refresh_all_cities)
    return {"message": "Scraping initiated for all cities"}

# Scrape events for a city
@app.post("/scrape/{city}")
async def scrape_events(city: str, background_tasks: BackgroundTasks):
    """Trigger scraping for a specific city"""
    from config import CONFIG
    if city not in CONFIG.get('SUPPORTED_LOCATIONS', []):
        raise HTTPException(status_code=404, detail=f"City {city} not supported")

    # Run scraping in background
    background_tasks.add_task(scrape_city_events, city)

    return {
        "message": f"Scraping initiated for {city}",
        "city": city,
        "note": "Events will be synced to shared database in real-time"
    }

# Subscribe to email updates
@app.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(subscription: SubscriptionCreate, db=Depends(get_db)):
    """Subscribe to email updates for a city"""
    from sqlalchemy import select
    from database import Subscription
    
    try:
        # Check if already subscribed
        existing = await db.execute(
            select(Subscription).where(
                (Subscription.email == subscription.email) &
                (Subscription.city == subscription.city)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already subscribed to this city")
        
        # Create subscription
        new_subscription = Subscription(
            email=subscription.email,
            city=subscription.city,
            is_active=True
        )
        
        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)
        
        return new_subscription
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Subscription failed due to an internal error")

# Unsubscribe
@app.delete("/subscribe/{subscription_id}")
async def unsubscribe(subscription_id: int, db=Depends(get_db)):
    """Unsubscribe from email updates"""
    from database import Subscription
    from sqlalchemy import select
    
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.is_active = False
    await db.commit()
    
    return {"message": "Unsubscribed successfully"}

# Admin login endpoint to generate tokens
@app.post("/admin/login")
async def admin_login(admin_credentials: dict, db=Depends(get_db)):
    """Admin login to generate JWT token"""
    from auth import create_access_token
    import os
    
    # In a real implementation, you would verify admin credentials against a database
    # For this implementation, we'll use a simple API key check
    admin_api_key = os.getenv("ADMIN_API_KEY")
    provided_api_key = admin_credentials.get("api_key")
    
    if not admin_api_key or provided_api_key != admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    # Create token with admin role
    token_data = {
        "sub": "admin_user",  # In a real app, this would be the actual user ID
        "role": "admin",
        "username": "admin"
    }
    
    token = create_access_token(data=token_data)
    return {"access_token": token, "token_type": "bearer"}

# Get all subscriptions (admin endpoint)
@app.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    city: Optional[str] = None,
    active_only: bool = True,
    current_user = Depends(get_current_admin),
    db=Depends(get_db)
):
    """Get all subscriptions with optional filtering - Admin only"""
    from sqlalchemy import select
    from database import Subscription

    query = select(Subscription)

    if city:
        query = query.where(Subscription.city == city)

    if active_only:
        query = query.where(Subscription.is_active == True)

    result = await db.execute(query)
    subscriptions = result.scalars().all()

    return subscriptions


# ============================================================================
# LOCATION API ROUTER
# ============================================================================

# Import and register location router
try:
    from backend.api.locations_router import router as locations_router
    app.include_router(locations_router)
    print("[OK] Location API router registered")
except ImportError as e:
    print(f"[WARN] Could not register location router: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
