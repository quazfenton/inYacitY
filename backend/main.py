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

# Pydantic models for API
class EventResponse(BaseModel):
    id: int
    title: str
    link: str
    date: str
    time: str
    location: str
    description: str
    source: str
    city_id: str
    
    class Config:
        from_attributes = True

import re

class SubscriptionCreate(BaseModel):
    email: EmailStr
    city_id: str

    @validator('email')
    def validate_email_format(cls, v):
        # Additional validation beyond Pydantic's EmailStr
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower().strip()  # Normalize email

    @validator('city_id')
    def validate_city(cls, v):
        from config import CONFIG
        supported = CONFIG.get('SUPPORTED_LOCATIONS', [])
        if v not in supported:
            raise ValueError(f'City {v} not supported')
        return v

class SubscriptionResponse(BaseModel):
    id: int
    email: str
    city_id: str
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
    init_db()
    yield
    # Shutdown: Close database connections
    pass

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
    
    for city_id in supported:
        city_info = CITY_MAPPING.get(city_id, {
            'id': city_id,
            'name': city_id.replace('--', ' ').title(),
            'slug': city_id.replace('--', '-').lower()
        })
        city_info['id'] = city_id
        cities.append(city_info)
    
    return {"cities": cities}

# Get events for a specific city
@app.get("/events/{city_id}", response_model=List[EventResponse])
async def get_city_events(
    city_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    db=Depends(get_db)
):
    """Get events for a specific city with optional date filtering"""
    from sqlalchemy import select
    from database import Event

    # Validate city
    from config import CONFIG
    supported_locations = CONFIG.get('SUPPORTED_LOCATIONS', [])
    if city_id not in supported_locations:
        raise HTTPException(status_code=404, detail=f"City {city_id} not supported")

    # Build query
    query = select(Event).where(Event.city_id == city_id)

    # Apply date filters if provided
    if start_date:
        query = query.where(Event.date >= start_date)
    if end_date:
        query = query.where(Event.date <= end_date)

    # Order by date and limit
    query = query.order_by(Event.date).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return events

# Scrape events for a city
@app.post("/scrape/{city_id}")
async def scrape_events(city_id: str, background_tasks: BackgroundTasks):
    """Trigger scraping for a specific city"""
    from config import CONFIG
    if city_id not in CONFIG.get('SUPPORTED_LOCATIONS', []):
        raise HTTPException(status_code=404, detail=f"City {city_id} not supported")
    
    # Run scraping in background
    background_tasks.add_task(scrape_city_events, city_id)
    
    return {"message": f"Scraping initiated for {city_id}", "city_id": city_id}

# Refresh all cities
@app.post("/scrape/all")
async def scrape_all(background_tasks: BackgroundTasks):
    """Trigger scraping for all supported cities"""
    background_tasks.add_task(refresh_all_cities)
    return {"message": "Scraping initiated for all cities"}

# Subscribe to email updates
@app.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(subscription: SubscriptionCreate, db=Depends(get_db)):
    """Subscribe to email updates for a city"""
    from sqlalchemy import select
    from database import Subscription
    
    # Check if already subscribed
    existing = await db.execute(
        select(Subscription).where(
            Subscription.email == subscription.email,
            Subscription.city_id == subscription.city_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already subscribed to this city")
    
    # Create subscription
    new_subscription = Subscription(
        email=subscription.email,
        city_id=subscription.city_id,
        is_active=True
    )
    
    db.add(new_subscription)
    await db.commit()
    await db.refresh(new_subscription)
    
    return new_subscription

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

# Get all subscriptions (admin endpoint)
@app.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    city_id: Optional[str] = None,
    active_only: bool = True,
    db=Depends(get_db)
):
    """Get all subscriptions with optional filtering"""
    from sqlalchemy import select
    from database import Subscription
    
    query = select(Subscription)
    
    if city_id:
        query = query.where(Subscription.city_id == city_id)
    
    if active_only:
        query = query.where(Subscription.is_active == True)
    
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return subscriptions

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
