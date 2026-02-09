#!/usr/bin/env python3
"""
Database models and initialization using SQLAlchemy with PostgreSQL
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, 
    Text, Index, Date, UniqueConstraint
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from datetime import datetime, date
import os

# Database URL from environment or default to PostgreSQL
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nocturne:nocturne@localhost:5432/nocturne"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_timeout=30,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

# Event model
class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    link = Column(String(1000), nullable=False, unique=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(String(100))
    location = Column(String(500))
    description = Column(Text)
    source = Column(String(50))  # 'eventbrite', 'meetup', 'luma'
    city_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for city + date queries
    __table_args__ = (
        Index('idx_events_city_date', 'city_id', 'date'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "location": self.location,
            "description": self.description,
            "source": self.source,
            "city_id": self.city_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# Subscription model
class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    city_id = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    unsubscribed_at = Column(DateTime)
    
    # Unique constraint on email + city_id
    __table_args__ = (
        UniqueConstraint('email', 'city_id', name='uq_email_city'),
        Index('idx_subscriptions_email_city', 'email', 'city_id'),
        Index('idx_subscriptions_active', 'city_id', 'is_active'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "city_id": self.city_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "unsubscribed_at": self.unsubscribed_at.isoformat() if self.unsubscribed_at else None,
        }

# Email log model (for tracking sent emails)
class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, nullable=False)
    email = Column(String(255), nullable=False)
    city_id = Column(String(100), nullable=False)
    subject = Column(String(500))
    sent_at = Column(DateTime, default=datetime.utcnow)
    events_count = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    __table_args__ = (
        Index('idx_email_logs_city_sent', 'city_id', 'sent_at'),
        Index('idx_email_logs_subscription', 'subscription_id'),
    )

# Dependency to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

# Initialize database tables
def init_db():
    """Create all tables in the database (sync wrapper for compatibility)"""
    import asyncio

    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    asyncio.run(_create_tables())

# Async version of init_db for use in async contexts
async def init_db_async():
    """Create all tables in the database (async version)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

# Drop all tables (use with caution!)
def drop_all_tables():
    """Drop all tables in the database"""
    import asyncio
    
    async def _drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    asyncio.run(_drop_tables())

# Helper functions for database operations
async def save_events(events_data: list, city_id: str):
    """Save or update events in the database with optimized batch processing"""
    from sqlalchemy import select, update, insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from datetime import datetime, date
    
    if not events_data:
        return {"saved": 0, "updated": 0}
    
    async with AsyncSessionLocal() as session:
        # Get all existing links in ONE query (O(1) instead of O(n))
        links = [e.get('link', '') for e in events_data if e.get('link')]
        existing_result = await session.execute(
            select(Event.link).where(Event.link.in_(links))
        )
        existing_links = {row[0] for row in existing_result.fetchall()}
        
        # Separate into new and existing events
        new_events = []
        update_events = []
        
        for event_data in events_data:
            link = event_data.get('link', '')
            
            # Parse date
            event_date = event_data.get('date')
            if isinstance(event_date, str):
                try:
                    event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
                except ValueError:
                    event_date = datetime.utcnow().date()
            elif not isinstance(event_date, date):
                event_date = datetime.utcnow().date()
            
            event_dict = {
                'title': event_data.get('title', 'Unknown'),
                'link': link,
                'date': event_date,
                'time': event_data.get('time', 'TBA'),
                'location': event_data.get('location', 'Location TBA'),
                'description': event_data.get('description', ''),
                'source': event_data.get('source', 'unknown'),
                'city_id': city_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            if link in existing_links:
                update_events.append(event_dict)
            else:
                new_events.append(event_dict)
        
        # Bulk insert new events (ONE query instead of O(n))
        saved_count = 0
        if new_events:
            await session.execute(
                insert(Event),
                new_events
            )
            saved_count = len(new_events)
        
        # Bulk update existing events (ONE query per batch)
        updated_count = 0
        if update_events:
            for event_dict in update_events:
                await session.execute(
                    update(Event)
                    .where(Event.link == event_dict['link'])
                    .values(
                        title=event_dict['title'],
                        date=event_dict['date'],
                        time=event_dict['time'],
                        location=event_dict['location'],
                        description=event_dict['description'],
                        source=event_dict['source'],
                        city_id=city_id,
                        updated_at=datetime.utcnow()
                    )
                )
            updated_count = len(update_events)
        
        await session.commit()
        return {"saved": saved_count, "updated": updated_count}

async def get_active_subscribers(city_id: str):
    """Get all active subscribers for a city"""
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.city_id == city_id,
                Subscription.is_active == True
            )
        )
        return result.scalars().all()

async def log_email_sent(subscription_id: int, email: str, city_id: str, events_count: int, success: bool = True, error_message: str = None):
    """Log an email sent event"""
    async with AsyncSessionLocal() as session:
        log_entry = EmailLog(
            subscription_id=subscription_id,
            email=email,
            city_id=city_id,
            sent_at=datetime.utcnow(),
            events_count=events_count,
            success=success,
            error_message=error_message
        )
        session.add(log_entry)
        await session.commit()
