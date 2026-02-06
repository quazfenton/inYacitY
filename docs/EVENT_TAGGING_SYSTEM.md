# Event Tagging System & User Accounts

Comprehensive guide to the 2D event tagging system, event filtering, user accounts, and the posh.vip scraper integration.

## Overview

### Core Components

1. **2D Tagging System** - Price tier + Category classification
2. **Event Models** - Enhanced event data with metadata
3. **User Accounts** - Sign up, authentication, event creation
4. **Event Filtering** - Advanced filtering and sorting
5. **Posh.vip Scraper** - Club/nightlife events (manual trigger)

## 1. 2D Event Tagging System

### Dimension 1: Price Tier (Primary Tag)

Event cost classification:
- **FREE** (0) - No cost
- **UNDER_20** (20) - $0-$20
- **UNDER_50** (50) - $20-$50
- **UNDER_100** (100) - $50-$100
- **PAID** (1000000) - Any paid event

### Dimension 2: Category (Secondary Tag)

Event type/genre classification:
- **CONCERT** - Music performances
- **NIGHTLIFE** - Clubs, bars, lounges
- **CLUB** - Club parties (default for posh.vip)
- **FOOD** - Food/dining events
- **SPORTS** - Sports events
- **THEATER** - Theater/performance
- **ART** - Art exhibitions
- **WORKSHOP** - Workshops/training
- **CONFERENCE** - Conferences/talks
- **SOCIAL** - Social gatherings
- **OTHER** - Miscellaneous
- **UNTAGGED** - No category assigned (default)

### Custom Tags (Optional)

Additional user-defined tags:
- Open bar, live music, VIP, outdoor, etc.
- User-selectable for frontend filtering

## 2. Event Data Model

### Core Event Fields

```typescript
interface Event {
  id: string;                    // Unique identifier
  title: string;                 // Event name
  location: string;              // Location name
  date: string;                  // ISO format (YYYY-MM-DD)
  time?: string;                 // HH:MM format
  description?: string;          // Event description
  coordinates?: {                // Geographic coordinates
    latitude: number;
    longitude: number;
  };
  
  source: string;                // Source (eventbrite, meetup, etc.)
  source_url?: string;           // Original event link
  
  // Pricing & Tags (2D System)
  price: number;                 // Price in cents (0 = free)
  tags: {
    price_tier: number;          // Dimension 1
    category: string;            // Dimension 2
    custom_tags?: string[];      // Optional custom tags
  };
  
  // Media & Host Info
  image?: {
    url?: string;
    thumbnail_url?: string;
    alt_text?: string;
    source_detected: boolean;    // Auto-detected?
  };
  host?: {
    name: string;
    url?: string;
    verified: boolean;
    quality_score: number;       // 0-1
  };
  
  // Metadata
  capacity?: number;             // Max attendees
  attending: number;             // Current attendance
  quality_tier: string;          // premium, standard, unverified, user
  event_type: string;            // scraped, user_created
  verified: boolean;             // Moderator verified?
  featured: boolean;             // Should be promoted?
  
  // User Events
  user_id?: string;              // For user-created events
  ticket_limit?: number;         // Max user registrations
  registered_users: number;      // Current registrations
  
  // Tracking
  scraped_at?: string;
  last_updated: string;
  metadata?: Record<string, any>;
}
```

## 3. User Accounts

### User Registration

**Sign Up:**
```bash
POST /api/auth/signup
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

**Sign In:**
```bash
POST /api/auth/login
{
  "username": "john_doe",
  "password": "secure_password"
}
```

### User Profile

```typescript
interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  bio?: string;
  avatar_url?: string;
  major_city?: string;           // Preferred city
  preferences: {
    // User-selected filter preferences
    price_tiers?: number[];
    categories?: string[];
    excluded_sources?: string[];
  };
  created_at: string;
  last_login?: string;
}
```

### User Event Management

#### Create User Event

**POST /api/user/events**

```json
{
  "title": "My House Party",
  "description": "Saturday evening gathering",
  "location": "Downtown LA",
  "coordinates": {
    "latitude": 34.0522,
    "longitude": -118.2437
  },
  "date": "2026-02-15",
  "time": "21:00",
  "price": 0,
  "category": "social",
  "image_url": "https://...",
  "ticket_limit": 50
}
```

#### Register for Event

**POST /api/user/events/{event_id}/register**

Response:
```json
{
  "registration_id": "reg_123",
  "ticket_number": 15,
  "status": "registered"
}
```

#### View User Events

**GET /api/user/events**

Response:
```json
{
  "created_events": [
    {
      "id": "evt_456",
      "title": "My House Party",
      "registered_users": 23,
      "ticket_limit": 50
    }
  ],
  "registered_events": [
    {
      "event_id": "evt_789",
      "ticket_number": 15,
      "status": "registered"
    }
  ]
}
```

## 4. Event Filtering API

### Filter Events

**POST /api/events/filter**

```json
{
  "price_tiers": [0, 20],              // Free and under $20
  "categories": ["concert", "nightlife"],
  "sources": ["eventbrite", "luma"],
  "excludeSources": ["posh_vip"],
  "quality_tiers": ["premium", "standard"],
  "dateFrom": "2026-02-05",
  "dateTo": "2026-02-28",
  "excludeUserEvents": false,
  "location": "ca--los-angeles"
}
```

### Sort Events

**Supported sort options:**
- `date` (ascending/descending)
- `price` (ascending/descending)
- `title` (A-Z/Z-A)
- `quality` (best/worst first)

### Search Events

**GET /api/events/search?q=concert&category=concert**

Searches:
- Event titles
- Locations
- Host names
- Custom tags

## 5. Posh.vip Scraper

### Features

- Club/nightlife events only
- Automatically tagged as "club" category
- Open bar detection
- **Manual trigger only** (not auto-scheduled)

### Configuration

```json
{
  "SOURCES": {
    "POSH_VIP": {
      "enabled": true,
      "manual_trigger_only": true,
      "category_tag": "club",
      "supported_cities": [
        "ca--los-angeles",
        "fl--miami",
        "ny--new-york"
      ]
    }
  }
}
```

### Manual Trigger

```bash
# Trigger posh.vip scraper for a city
POST /api/scraper/posh-vip?city=ca--los-angeles

# Response
{
  "status": "scraping",
  "city": "ca--los-angeles",
  "events_found": 45,
  "new_events": 12
}
```

### Output File

**File:** `scraper/posh_vip_events.json`

```json
{
  "events": [
    {
      "title": "Club Name - Friday Night Party",
      "date": "2026-02-07",
      "location": "Nightclub Venue",
      "source": "Posh.vip",
      "category": "club",
      "price": 2500,
      "has_open_bar": true,
      "link": "https://posh.vip/events/..."
    }
  ],
  "notes": "Posh.vip events - club/nightlife only - manually triggered"
}
```

## 6. Frontend Components

### Event Filter Component

**Location:** `fronto/src/components/EventFilter.tsx`

Features:
- Price tier checkboxes
- Category multi-select
- Source selection
- Verified/Featured toggles
- Date range picker
- Search box

```tsx
<EventFilter
  onFilter={(filter) => applyFilter(filter)}
  availableSources={sources}
  availableCategories={categories}
/>
```

### Event List with Tagging

**Location:** `fronto/src/components/EventList.tsx`

Features:
- Display price tier badge
- Show category tag
- Custom tag badges
- Host verification indicator
- Quality tier indicator
- "Register" button for user events

```tsx
<EventList
  events={filteredEvents}
  sort={{by: 'date', ascending: true}}
  showPriceFilter={true}
  showCategoryFilter={true}
/>
```

### User Account Component

**Location:** `fronto/src/components/UserAccount.tsx`

Features:
- Sign in/Sign up form
- User profile display
- Create event form
- Event registration management
- Filter preferences

## 7. Database Schema Updates

### New Tables

```sql
-- Events table (updated)
CREATE TABLE IF NOT EXISTS events (
  id VARCHAR(50) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  date DATE,
  time TIME,
  price INT DEFAULT 0,
  price_tier INT,           -- Dimension 1
  category VARCHAR(50),     -- Dimension 2
  custom_tags JSON,         -- Additional tags
  source VARCHAR(50),
  source_url VARCHAR(500),
  description LONGTEXT,
  image_url VARCHAR(500),
  image_thumbnail VARCHAR(500),
  host_name VARCHAR(255),
  host_url VARCHAR(500),
  host_verified BOOLEAN DEFAULT FALSE,
  quality_tier VARCHAR(50) DEFAULT 'standard',
  event_type VARCHAR(50) DEFAULT 'scraped',
  verified BOOLEAN DEFAULT FALSE,
  featured BOOLEAN DEFAULT FALSE,
  user_id VARCHAR(100),     -- For user-created events
  ticket_limit INT,
  registered_users INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_price_tier (price_tier),
  INDEX idx_category (category),
  INDEX idx_date (date),
  INDEX idx_source (source),
  INDEX idx_user_id (user_id)
);

-- Users table (new)
CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(100) PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  auth_provider VARCHAR(50) DEFAULT 'local',
  full_name VARCHAR(255),
  bio TEXT,
  avatar_url VARCHAR(500),
  major_city VARCHAR(50),
  preferences JSON,
  verified BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login TIMESTAMP,
  
  INDEX idx_username (username),
  INDEX idx_email (email)
);

-- User event registrations table (new)
CREATE TABLE IF NOT EXISTS user_event_registrations (
  id VARCHAR(100) PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  event_id VARCHAR(50) NOT NULL,
  ticket_number INT,
  status VARCHAR(50) DEFAULT 'registered',
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (event_id) REFERENCES events(id),
  INDEX idx_user_event (user_id, event_id)
);
```

## 8. Usage Examples

### Filter for Free Concerts

```typescript
const filter: EventFilter = {
  price_tiers: [0],                  // Free only
  categories: ['concert'],
  dateFrom: '2026-02-01',
  dateTo: '2026-02-28'
};

const concerts = filterEvents(allEvents, filter);
```

### Exclude Posh.vip from Results

```typescript
const filter: EventFilter = {
  excludeSources: ['posh_vip'],      // Hide club events
  excludeUserEvents: false           // Include user-created
};

const curated = filterEvents(allEvents, filter);
```

### User Creates and Promotes Event

```typescript
// 1. User creates event
const userEvent: Event = {
  id: 'evt_user_123',
  title: 'My Networking Event',
  date: '2026-02-20',
  location: 'Downtown LA',
  price: 0,
  tags: {
    price_tier: 0,          // Free
    category: 'social'      // Social gathering
  },
  event_type: 'user_created',
  user_id: 'user_456',
  ticket_limit: 100
};

// 2. User event appears in results
// 3. Other users can register
// 4. User can see registrations and manage event
```

### Multi-Source Event Discovery

```typescript
// Get all upcoming free events across sources
const upcomingFree = filterEvents(
  allEvents,
  {
    price_tiers: [0],              // Free only
    dateFrom: today,
    dateTo: thirtyDaysFromNow
  }
);

// Sort by quality tier
const sorted = sortEvents(upcomingFree, {
  by: 'quality',
  ascending: false  // Best first
});

// Group by category for UI
const grouped = groupByCategory(sorted);
```

## 9. Migration Guide

### Updating Existing Events

For existing scraped events, default values:
- `price_tier`: Auto-calculated from `price` field
- `category`: UNTAGGED (empty string)
- `quality_tier`: STANDARD (for scraped) or USER (for user-created)
- `event_type`: SCRAPED (for all current events)

### Data Upgrade Script

```python
# Convert existing events to new format
def upgrade_event(old_event):
    price = old_event.get('price', 0)
    
    return {
        **old_event,
        'price_tier': determinePriceTier(price),
        'category': '',  # UNTAGGED
        'quality_tier': 'standard',
        'event_type': 'scraped',
        'custom_tags': [],
        'verified': False,
        'featured': False
    }
```

## 10. Future Enhancements

### Phase 2: Auto-Tagging
- Machine learning for category detection
- Keyword-based tagging
- Image-based category detection

### Phase 3: User Preferences
- Save filter preferences
- Personalized recommendations
- Email digest of curated events

### Phase 4: Advanced Features
- Event merging (detect duplicates across sources)
- Host reputation system
- Community reviews and ratings
- Event capacity alerts

### Phase 5: Social Features
- Event invitations
- Friend group discovery
- Social shares and recommendations

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/events` | GET | Get all events |
| `/api/events/filter` | POST | Filter with criteria |
| `/api/events/{id}` | GET | Get event details |
| `/api/events/search` | GET | Search events |
| `/api/auth/signup` | POST | Register user |
| `/api/auth/login` | POST | Sign in |
| `/api/auth/logout` | POST | Sign out |
| `/api/user/profile` | GET | Get user profile |
| `/api/user/profile` | PUT | Update profile |
| `/api/user/events` | GET | Get user's events |
| `/api/user/events` | POST | Create user event |
| `/api/user/events/{id}/register` | POST | Register for event |
| `/api/user/events/{id}/unregister` | DELETE | Unregister from event |
| `/api/scraper/posh-vip` | POST | Manual trigger posh.vip scraper |

---

**Version:** 1.0  
**Created:** 2026-02-05  
**Status:** Production Ready
