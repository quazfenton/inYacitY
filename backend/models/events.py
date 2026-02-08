"""
Event Data Models with 2D Tagging System

Supports:
- Event hierarchy (free vs paid, tier classification)
- 2D tagging (primary: price tier, secondary: category tag)
- Event metadata (image, host, quality tier)
- Source tracking
- User events vs scraped events
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class PriceTier(Enum):
    """Event price classification (Primary Tag - Dimension 1)"""
    FREE = 0
    UNDER_20 = 20
    UNDER_50 = 50
    UNDER_100 = 100
    PAID = 1000000  # Any paid event


class EventCategory(Enum):
    """Event categories (Secondary Tag - Dimension 2)"""
    CONCERT = "concert"
    NIGHTLIFE = "nightlife"
    CLUB = "club"
    FOOD = "food"
    SPORTS = "sports"
    THEATER = "theater"
    ART = "art"
    WORKSHOP = "workshop"
    CONFERENCE = "conference"
    SOCIAL = "social"
    OTHER = "other"
    UNTAGGED = ""  # Default for manually untagged events


class EventSource(Enum):
    """Event source identifier"""
    EVENTBRITE = "eventbrite"
    MEETUP = "meetup"
    LUMA = "luma"
    DICE_FM = "dice_fm"
    RA_CO = "ra_co"
    POSH_VIP = "posh_vip"
    USER_CREATED = "user_created"


class EventQualityTier(Enum):
    """Event quality classification"""
    PREMIUM = "premium"       # Hand-verified, high-quality events
    STANDARD = "standard"     # Normal scraped events
    UNVERIFIED = "unverified" # Auto-detected, needs verification
    USER = "user"             # User-created events


class EventType(Enum):
    """Type of event"""
    SCRAPED = "scraped"       # From external source
    USER_CREATED = "user_created"  # Created by user


@dataclass
class EventImage:
    """Event image/thumbnail data"""
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    alt_text: Optional[str] = None
    source_detected: bool = False  # Was image auto-detected?

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'thumbnail_url': self.thumbnail_url,
            'alt_text': self.alt_text,
            'source_detected': self.source_detected
        }

    @staticmethod
    def from_dict(data: dict) -> 'EventImage':
        if not data:
            return EventImage()
        return EventImage(
            url=data.get('url'),
            thumbnail_url=data.get('thumbnail_url'),
            alt_text=data.get('alt_text'),
            source_detected=data.get('source_detected', False)
        )


@dataclass
class EventHost:
    """Event host/creator information"""
    name: str
    url: Optional[str] = None
    verified: bool = False
    quality_score: float = 0.0  # 0-1, for host reputation

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'url': self.url,
            'verified': self.verified,
            'quality_score': self.quality_score
        }

    @staticmethod
    def from_dict(data: dict) -> Optional['EventHost']:
        if not data or not data.get('name'):
            return None
        return EventHost(
            name=data['name'],
            url=data.get('url'),
            verified=data.get('verified', False),
            quality_score=float(data.get('quality_score', 0.0))
        )


@dataclass
class EventTags:
    """2D Tag Structure for Events
    
    Dimension 1: Price Tier (primary classification)
    Dimension 2: Category (secondary classification)
    """
    price_tier: PriceTier = PriceTier.FREE  # Dimension 1: Price
    category: EventCategory = EventCategory.UNTAGGED  # Dimension 2: Category
    custom_tags: List[str] = field(default_factory=list)  # Additional user tags

    def to_dict(self) -> dict:
        return {
            'price_tier': self.price_tier.value,
            'category': self.category.value,
            'custom_tags': self.custom_tags
        }

    @staticmethod
    def from_dict(data: dict) -> 'EventTags':
        if not data:
            return EventTags()
        
        price_val = data.get('price_tier', 0)
        price_tier = next(
            (p for p in PriceTier if p.value == price_val),
            PriceTier.FREE
        )
        
        category_val = data.get('category', '')
        category = next(
            (c for c in EventCategory if c.value == category_val),
            EventCategory.UNTAGGED
        )
        
        return EventTags(
            price_tier=price_tier,
            category=category,
            custom_tags=data.get('custom_tags', [])
        )


@dataclass
class Event:
    """
    Event data model with 2D tagging system
    
    Attributes:
        id: Unique event identifier
        title: Event name
        description: Event description
        date: Event date (ISO format)
        time: Event time (HH:MM format)
        location: Physical location name
        coordinates: Geographic coordinates
        source: Where the event came from
        source_url: Link to original event
        
        # Pricing & Tags (2D System)
        price: Actual price in cents (or 0 for free)
        tags: 2D tag structure (price tier + category)
        
        # Media & Host Info
        image: Event image/thumbnail
        host: Event creator/host information
        
        # Metadata
        capacity: Max attendees
        attending: Current attendance count
        quality_tier: Quality classification
        event_type: Scraped vs user-created
        verified: Is event verified by moderator?
        featured: Should event be featured/promoted?
        
        # Tracking
        scraped_at: When event was scraped
        last_updated: Last modification time
        metadata: Flexible additional data
    """
    
    # Core Fields
    id: str
    title: str
    location: str
    date: str  # YYYY-MM-DD
    time: Optional[str] = "TBA"
    description: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    
    # Source Info
    source: EventSource = EventSource.EVENTBRITE
    source_url: Optional[str] = None
    
    # Pricing & Tags (2D System)
    price: int = 0  # Price in cents (0 = free)
    tags: EventTags = field(default_factory=EventTags)
    
    # Media & Host
    image: EventImage = field(default_factory=EventImage)
    host: Optional[EventHost] = None
    
    # Metadata
    capacity: Optional[int] = None
    attending: int = 0
    quality_tier: EventQualityTier = EventQualityTier.STANDARD
    event_type: EventType = EventType.SCRAPED
    verified: bool = False
    featured: bool = False
    
    # User Events
    user_id: Optional[str] = None  # For user-created events
    ticket_limit: Optional[int] = None  # Max user registrations
    registered_users: int = 0  # Current registrations

    # City association (added for city-based filtering)
    city_id: Optional[str] = None  # City ID that the event was scraped for
    
    # Tracking
    scraped_at: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize event to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'location': self.location,
            'date': self.date,
            'time': self.time,
            'description': self.description,
            'coordinates': self.coordinates,
            'source': self.source.value,
            'source_url': self.source_url,
            'price': self.price,
            'price_tier': self.tags.price_tier.value,
            'category': self.tags.category.value,
            'tags': self.tags.to_dict(),
            'image': self.image.to_dict(),
            'host': self.host.to_dict() if self.host else None,
            'capacity': self.capacity,
            'attending': self.attending,
            'quality_tier': self.quality_tier.value,
            'event_type': self.event_type.value,
            'verified': self.verified,
            'featured': self.featured,
            'user_id': self.user_id,
            'ticket_limit': self.ticket_limit,
            'registered_users': self.registered_users,
            'city_id': self.city_id,
            'scraped_at': self.scraped_at,
            'last_updated': self.last_updated,
            'metadata': self.metadata
        }

    @staticmethod
    def from_dict(data: dict) -> 'Event':
        """Deserialize event from dictionary"""
        source_val = data.get('source', 'eventbrite')
        source = next(
            (s for s in EventSource if s.value == source_val),
            EventSource.EVENTBRITE
        )
        
        event_type_val = data.get('event_type', 'scraped')
        event_type = next(
            (et for et in EventType if et.value == event_type_val),
            EventType.SCRAPED
        )
        
        quality_tier_val = data.get('quality_tier', 'standard')
        quality_tier = next(
            (qt for qt in EventQualityTier if qt.value == quality_tier_val),
            EventQualityTier.STANDARD
        )
        
        return Event(
            id=data['id'],
            title=data['title'],
            location=data['location'],
            date=data['date'],
            time=data.get('time'),
            description=data.get('description'),
            coordinates=data.get('coordinates'),
            source=source,
            source_url=data.get('source_url'),
            price=data.get('price', 0),
            tags=EventTags.from_dict(data.get('tags', {})),
            image=EventImage.from_dict(data.get('image')),
            host=EventHost.from_dict(data.get('host')),
            capacity=data.get('capacity'),
            attending=data.get('attending', 0),
            quality_tier=quality_tier,
            event_type=event_type,
            verified=data.get('verified', False),
            featured=data.get('featured', False),
            user_id=data.get('user_id'),
            ticket_limit=data.get('ticket_limit'),
            registered_users=data.get('registered_users', 0),
            city_id=data.get('city_id'),
            scraped_at=data.get('scraped_at'),
            last_updated=data.get('last_updated', datetime.utcnow().isoformat()),
            metadata=data.get('metadata', {})
        )


@dataclass
class EventFilter:
    """
    Event filter criteria for querying and displaying events
    
    Supports filtering on:
    - Price tier (free, paid)
    - Category (concert, nightlife, etc.)
    - Source
    - Quality tier
    - Verified status
    - Location
    - Date range
    """
    price_tiers: Optional[List[PriceTier]] = None
    categories: Optional[List[EventCategory]] = None
    sources: Optional[List[EventSource]] = None
    quality_tiers: Optional[List[EventQualityTier]] = None
    verified_only: bool = False
    featured_only: bool = False
    location_codes: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    custom_tags: Optional[List[str]] = None
    exclude_user_events: bool = False
    exclude_sources: Optional[List[EventSource]] = None

    def matches(self, event: Event) -> bool:
        """Check if event matches filter criteria"""
        
        # Price tier filter
        if self.price_tiers and event.tags.price_tier not in self.price_tiers:
            return False
        
        # Category filter
        if self.categories and event.tags.category not in self.categories:
            return False
        
        # Source filter
        if self.sources and event.source not in self.sources:
            return False
        if self.exclude_sources and event.source in self.exclude_sources:
            return False
        
        # Quality tier filter
        if self.quality_tiers and event.quality_tier not in self.quality_tiers:
            return False
        
        # Verified filter
        if self.verified_only and not event.verified:
            return False
        
        # Featured filter
        if self.featured_only and not event.featured:
            return False
        
        # Date range filter
        if self.date_from and event.date < self.date_from:
            return False
        if self.date_to and event.date > self.date_to:
            return False
        
        # Custom tags filter
        if self.custom_tags:
            event_tags = set(event.tags.custom_tags)
            filter_tags = set(self.custom_tags)
            if not event_tags.intersection(filter_tags):
                return False
        
        # User events filter
        if self.exclude_user_events and event.event_type == EventType.USER_CREATED:
            return False
        
        return True

    def to_dict(self) -> dict:
        """Serialize filter to dictionary"""
        return {
            'price_tiers': [p.value for p in self.price_tiers] if self.price_tiers else None,
            'categories': [c.value for c in self.categories] if self.categories else None,
            'sources': [s.value for s in self.sources] if self.sources else None,
            'quality_tiers': [qt.value for qt in self.quality_tiers] if self.quality_tiers else None,
            'verified_only': self.verified_only,
            'featured_only': self.featured_only,
            'location_codes': self.location_codes,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'custom_tags': self.custom_tags,
            'exclude_user_events': self.exclude_user_events,
            'exclude_sources': [s.value for s in self.exclude_sources] if self.exclude_sources else None
        }


class EventStore:
    """
    In-memory event storage with filtering and querying
    
    Supports:
    - Event CRUD
    - Filtering by tags and metadata
    - Sorting options
    - Duplicate detection
    """
    
    def __init__(self):
        """Initialize event store"""
        self.events: Dict[str, Event] = {}
        self.source_links: Dict[str, str] = {}  # Track source URLs to detect duplicates

    def add_event(self, event: Event) -> bool:
        """
        Add event to store
        
        Args:
            event: Event object
            
        Returns:
            True if added, False if duplicate (by ID or source URL)
        """
        # Check for duplicate by event ID
        if event.id in self.events:
            return False

        # Check for duplicate by source URL
        if event.source_url and event.source_url in self.source_links:
            return False
        
        self.events[event.id] = event
        if event.source_url:
            self.source_links[event.source_url] = event.id
        
        return True
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self.events.get(event_id)

    def filter_events(self, filter_: EventFilter, limit: int = 100) -> List[Event]:
        """
        Filter events with criteria
        
        Args:
            filter_: EventFilter object with criteria
            limit: Max results
            
        Returns:
            List of matching events
        """
        matching = [e for e in self.events.values() if filter_.matches(e)]
        return matching[:limit]

    def sort_events(
        self,
        events: List[Event],
        sort_by: str = 'date',
        ascending: bool = True
    ) -> List[Event]:
        """
        Sort events by criteria
        
        Args:
            events: List of events
            sort_by: 'date', 'price', 'title', 'quality'
            ascending: Sort direction
            
        Returns:
            Sorted list
        """
        if sort_by == 'date':
            return sorted(events, key=lambda e: e.date, reverse=not ascending)
        elif sort_by == 'price':
            return sorted(events, key=lambda e: e.price, reverse=not ascending)
        elif sort_by == 'title':
            return sorted(events, key=lambda e: e.title, reverse=not ascending)
        elif sort_by == 'quality':
            quality_order = {
                EventQualityTier.PREMIUM: 4,
                EventQualityTier.STANDARD: 3,
                EventQualityTier.UNVERIFIED: 2,
                EventQualityTier.USER: 1
            }
            return sorted(
                events,
                key=lambda e: quality_order.get(e.quality_tier, 0),
                reverse=not ascending
            )
        else:
            return events

    def get_stats(self) -> dict:
        """Get store statistics"""
        if not self.events:
            return {
                'total': 0,
                'by_source': {},
                'by_category': {},
                'by_price_tier': {}
            }
        
        stats = {
            'total': len(self.events),
            'by_source': {},
            'by_category': {},
            'by_price_tier': {},
            'by_quality_tier': {}
        }
        
        for event in self.events.values():
            # Source stats
            source = event.source.value
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
            
            # Category stats
            category = event.tags.category.value
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Price tier stats
            price_tier = event.tags.price_tier.value
            stats['by_price_tier'][str(price_tier)] = stats['by_price_tier'].get(str(price_tier), 0) + 1
            
            # Quality tier stats
            quality = event.quality_tier.value
            stats['by_quality_tier'][quality] = stats['by_quality_tier'].get(quality, 0) + 1
        
        return stats
