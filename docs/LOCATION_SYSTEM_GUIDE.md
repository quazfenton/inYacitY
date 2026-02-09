# Location-Based System Guide

Comprehensive geolocation and proximity-based location system for personalized event discovery.

## Overview

The location system enables:

1. **Browser Geolocation Detection** - Auto-detect user location via browser API
2. **City Hierarchy** - Major cities → Secondary cities/towns → Fine-grained locations
3. **Proximity-Based Filtering** - Find events near user's location
4. **User Preferences** - Store location preference with cookie/localStorage
5. **Modular API** - Extensible for other services and use cases

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  CitySelector Component + Geolocation Utils             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ↓
┌─────────────────────────────────────────────────────────┐
│              Backend API (Flask/Express)                │
│  locations_api.py - REST endpoints for location queries│
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ SQL Queries
                       ↓
┌─────────────────────────────────────────────────────────┐
│            Database (MySQL/PostgreSQL)                   │
│  - locations table (major cities, secondary cities)     │
│  - user_location_preferences (user preferences)         │
│  - location_history (analytics)                         │
│  - nearby_locations_cache (performance)                 │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- Python (models/locations.py)
- Flask (api/locations_api.py)
- MySQL/PostgreSQL (migrations/001_create_locations_schema.sql)

**Frontend:**
- React/TypeScript (CitySelector.tsx)
- Browser Geolocation API
- localStorage/cookies

## Data Model

### Location Hierarchy

```
Major City (Tier 1)
  ├── Coordinates (lat/long)
  ├── Population
  ├── Timezone
  └── Secondary City (Tier 2)
        └── Fine-grained coordinates
```

### Location Tiers

1. **Major City** (MAJOR_CITY)
   - Primary event aggregation points
   - 18 pre-configured cities
   - Used as primary UI selector

2. **Secondary City** (SECONDARY_CITY)
   - Suburbs and nearby towns
   - Parent reference to major city
   - Shown after major city selection

3. **Town** (TOWN)
   - Smaller settlements
   - Future expansion

4. **Region** (REGION)
   - Larger geographic areas
   - For broader filtering

## API Endpoints

### Discovery Endpoints

#### Get All Major Cities
```bash
GET /api/locations/major-cities
```

**Query Parameters:**
- `sort_by` - 'name', 'population', or 'distance_from'
- `country` - Filter by country code (e.g., 'US', 'CA')
- `limit` - Max results (default: 50)
- `lat`, `lon` - Required if sort_by='distance_from'

**Response:**
```json
{
  "success": true,
  "count": 18,
  "cities": [
    {
      "id": "ca-la",
      "code": "ca--los-angeles",
      "name": "Los Angeles, CA",
      "tier": "major",
      "coordinates": {
        "latitude": 34.0522,
        "longitude": -118.2437
      },
      "state": "CA",
      "country": "US",
      "population": 3979576,
      "timezone": "America/Los_Angeles"
    }
  ]
}
```

#### Get Location by Code
```bash
GET /api/locations/location/{code}
```

**Example:**
```bash
GET /api/locations/location/ca--los-angeles
```

**Response:**
```json
{
  "success": true,
  "location": {
    "code": "ca--los-angeles",
    "name": "Los Angeles, CA",
    "coordinates": { ... },
    "secondary_cities": [ ... ]  // If major city
  }
}
```

### Geolocation Endpoints

#### Find Nearest Cities
```bash
POST /api/locations/nearest-cities
```

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "limit": 5
}
```

**Response:**
```json
{
  "success": true,
  "center": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "results": [
    {
      "location": { ... },
      "distance_miles": 0.0
    }
  ]
}
```

#### Get Nearby Locations
```bash
POST /api/locations/nearby
```

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "radius_miles": 25.0,
  "tier": "major"  // optional
}
```

**Response:**
```json
{
  "success": true,
  "center": { ... },
  "radius_miles": 25.0,
  "count": 5,
  "results": [
    {
      "location": { ... },
      "distance_miles": 12.5
    }
  ]
}
```

### User Preference Endpoints

#### Save Location Preference
```bash
POST /api/locations/preferences
```

**Request Body:**
```json
{
  "user_id": "user_123",
  "major_city_code": "ca--los-angeles",
  "secondary_location": {
    "latitude": 34.0522,
    "longitude": -118.2437
  },
  "auto_detect": true,
  "preferred_radius": 25.0
}
```

**Response:**
```json
{
  "success": true,
  "message": "Location preference saved",
  "preference": { ... }
}
```

#### Get User Preference
```bash
GET /api/locations/preferences/{user_id}
```

### Search Endpoints

#### Search Locations
```bash
GET /api/locations/search?q=los+angeles&tier=major&limit=20
```

**Query Parameters:**
- `q` - Search query (min 2 chars)
- `tier` - Filter by tier
- `country` - Filter by country
- `limit` - Max results

**Response:**
```json
{
  "success": true,
  "query": "los angeles",
  "count": 2,
  "results": [
    {
      "code": "ca--los-angeles",
      "name": "Los Angeles, CA",
      ...
    }
  ]
}
```

## Frontend Integration

### CitySelector Component

Display major cities with auto-detection:

```tsx
import CitySelector from '@/components/CitySelector';

function MyApp() {
  return (
    <CitySelector
      onCitySelect={(cityCode) => {
        console.log(`Selected: ${cityCode}`);
        // Filter events by city
      }}
      showAutoDetect={true}
      showSecondaryLocations={true}
    />
  );
}
```

### Geolocation Utils

Manual geolocation detection:

```typescript
import {
  initializeLocationDetection,
  findNearestCity,
  getNearbyLocations,
  saveLocationPreference,
  getLocationPreference
} from '@/utils/geolocation';

// Auto-detect and find nearest city
const nearestCityCode = await initializeLocationDetection();

// Get user's browser location
const coords = await getUserLocation();

// Find nearest major city
const nearest = await findNearestCity(coords);

// Get nearby locations within radius
const nearby = await getNearbyLocations(coords, 25);

// Save preference
saveLocationPreference('ca--los-angeles', coords, true, 25);

// Retrieve saved preference
const pref = getLocationPreference();
```

## Database Schema

### Main Tables

1. **locations** - All geographic locations
   - Coordinates (lat/long)
   - Tier classification
   - Parent city reference
   - Timezone information

2. **user_location_preferences** - User preferences
   - Major city code
   - Fine-grained coordinates
   - Auto-detect setting
   - Preferred search radius

3. **location_history** - User location history
   - Detection method (browser, IP, manual)
   - Accuracy information
   - Timestamp and session tracking

4. **location_events_summary** - Event counts by location
   - Total events
   - Free events
   - Upcoming events (30 days)

5. **nearby_locations_cache** - Cached proximity queries
   - Distance calculations
   - Expiration time

### Stored Procedures

```sql
-- Find nearby locations within radius
CALL find_nearby_locations(40.7128, -74.0060, 25);

-- Update event counts for location
CALL update_location_event_counts('ca--los-angeles');
```

### Views

```sql
-- View major cities with event statistics
SELECT * FROM major_cities_with_stats;

-- View user location preferences with checkins
SELECT * FROM user_location_preferences_view;
```

## Performance Optimization

### Caching Strategy

1. **Browser Cache** (24 hours)
   - User's device coordinates
   - Location preferences (localStorage)

2. **Database Cache**
   - Nearby locations (within radius)
   - Expires after configurable period

3. **API Response Caching**
   - GET requests cached (5 minutes)
   - Invalidate on updates

### Indexes for Speed

```sql
-- Coordinate indexes for distance queries
CREATE INDEX idx_locations_lat_lon ON locations (latitude, longitude);

-- User preference lookups
CREATE INDEX idx_user_prefs_major_city ON user_location_preferences (major_city_code);

-- Historical data queries
CREATE INDEX idx_location_history_user_timestamp ON location_history (user_id, timestamp);
```

### Haversine Formula (Distance Calculation)

```python
def distance_to(lat1, lon1, lat2, lon2) -> float:
    """Calculate distance in miles"""
    R = 3959  # Earth's radius in miles
    lat1, lon1 = radians(lat1), radians(lon1)
    lat2, lon2 = radians(lat2), radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin²(dlat/2) + cos(lat1)cos(lat2)sin²(dlon/2)
    c = 2·arcsin(√a)
    return R · c
```

## Use Cases

### 1. Auto-Scroll to User's City

On page load:
1. Request browser geolocation (with user consent)
2. Find nearest major city
3. Auto-scroll city list to highlight nearest city
4. Save preference in localStorage

**Result:** User sees their city at top of list on return visits.

### 2. Fine-Grained Location Filtering

After selecting major city:
1. Display secondary cities/towns nearby
2. Allow selection of specific town
3. Filter events by proximity (within X miles)
4. Store preference for recommendations

**Result:** User gets events closest to them, not just the major city.

### 3. Proximity-Based Recommendations

1. Track user's location history
2. Calculate frequently visited areas
3. Recommend events near those areas
4. Show distance to each event

**Result:** Personalized recommendations improving engagement.

### 4. Multi-Service Location Queries

Use location API for:
- Venue/restaurant discovery
- Meetup suggestions
- Local business directory
- Real estate listings

**Result:** Reusable location system across products.

## Configuration

### Supported Cities

**18 Pre-configured Major Cities:**

**United States (17):**
- California: Los Angeles, San Francisco, San Diego
- Colorado: Denver
- Washington DC
- Florida: Miami
- Georgia: Atlanta
- Illinois: Chicago
- Massachusetts: Boston
- Nevada: Las Vegas
- New York: New York
- Pennsylvania: Philadelphia
- Texas: Austin, Dallas, Houston
- Utah: Salt Lake City
- Washington: Seattle

**Canada (1):**
- Ontario: Toronto

### Environment Variables

```env
# API Configuration
LOCATION_API_BASE_URL=/api/locations
LOCATION_CACHE_DURATION=24h
LOCATION_SEARCH_RADIUS=25

# Geolocation
ENABLE_AUTO_DETECT=true
GEOLOCATION_TIMEOUT=10000
GEOLOCATION_MAX_AGE=60000

# Database
LOCATION_DB_HOST=localhost
LOCATION_DB_USER=root
LOCATION_DB_PASSWORD=password
LOCATION_DB_NAME=inyacity
```

## Migration & Setup

### 1. Database Setup

```bash
# Run migrations
mysql -u root -p inyacity < backend/migrations/001_create_locations_schema.sql

# Verify
mysql -u root -p inyacity -e "SELECT COUNT(*) FROM locations;"
```

### 2. Backend Setup

```bash
# Install dependencies
pip install flask

# Run API
python -m flask run --host=0.0.0.0 --port=5000
```

### 3. Frontend Setup

```bash
# Install dependencies
npm install

# Import components
import CitySelector from '@/components/CitySelector';
import { getUserLocation } from '@/utils/geolocation';
```

## Testing

### API Testing

```bash
# Get major cities
curl http://localhost:5000/api/locations/major-cities

# Find nearest cities
curl -X POST http://localhost:5000/api/locations/nearest-cities \
  -H "Content-Type: application/json" \
  -d '{"latitude": 40.7128, "longitude": -74.0060}'

# Get nearby locations
curl -X POST http://localhost:5000/api/locations/nearby \
  -H "Content-Type: application/json" \
  -d '{"latitude": 40.7128, "longitude": -74.0060, "radius_miles": 25}'
```

### Frontend Testing

```typescript
// Test geolocation
const coords = await getUserLocation();
console.log('User location:', coords);

// Test nearest city
const nearest = await findNearestCity(coords);
console.log('Nearest city:', nearest);

// Test preference storage
saveLocationPreference('ca--los-angeles');
const pref = getLocationPreference();
console.log('Saved preference:', pref);
```

## Future Enhancements

### Phase 2: Secondary Cities

1. Populate secondary cities for each major city
2. Create tier 2 UI selector after major city selection
3. Filter events by secondary city
4. Distance-based sorting

### Phase 3: IP-Based Geolocation

1. Add IP geolocation fallback (MaxMind GeoIP2)
2. Auto-detect when browser geolocation unavailable
3. Store IP detection history

### Phase 4: Recommendations

1. Track user's location history
2. Build recommendation algorithm
3. Suggest new events based on location patterns
4. Cross-product recommendations (venues, restaurants)

### Phase 5: Advanced Analytics

1. Heatmaps of popular locations
2. Event clustering by region
3. Seasonal location trends
4. User movement patterns

## Troubleshooting

### Geolocation Not Working

**Issue:** Browser geolocation returns null
**Solutions:**
- Check HTTPS (required for geolocation)
- Verify browser permissions
- Use IP fallback for non-compliant browsers

### Distance Calculations Off

**Issue:** Distances don't match reality
**Solutions:**
- Verify coordinates are correct (WGS84)
- Account for routing (straight-line vs. road distance)
- Consider elevation changes

### Performance Issues

**Issue:** Slow proximity queries
**Solutions:**
- Use nearby_locations_cache table
- Implement grid-based indexing
- Consider PostGIS for PostgreSQL
- Cache API responses

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/locations/major-cities` | GET | Get all major cities |
| `/locations/location/{code}` | GET | Get location details |
| `/locations/nearest-cities` | POST | Find nearest cities |
| `/locations/nearby` | POST | Get nearby locations |
| `/locations/preferences` | POST | Save user preference |
| `/locations/preferences/{id}` | GET | Get user preference |
| `/locations/search` | GET | Search locations |
| `/locations/stats` | GET | Database statistics |
| `/locations/health` | GET | Health check |

---

**Version:** 1.0  
**Last Updated:** 2026-02-05  
**Status:** Production Ready
