# Advanced Location System Documentation

Complete implementation guide for the advanced geolocation system with proximity-based event discovery.

## What's Implemented

### Backend (FastAPI)

✅ **Location Router** (`backend/api/locations_router.py`)
- `/api/locations/major-cities` - Get all major cities with filtering
- `/api/locations/location/{code}` - Get specific city details
- `/api/locations/nearest-cities` - Find nearest cities to coordinates
- `/api/locations/nearby` - Get cities within radius
- `/api/locations/preferences` - Save/load user preferences
- `/api/locations/search` - Search locations by name
- `/api/locations/events/nearby` - Get events within radius
- `/api/locations/events/by-city/{code}` - Get events by city
- `/api/locations/stats` - Location database statistics
- `/api/locations/health` - Health check

✅ **Location Models** (`backend/models/locations.py`)
- `Coordinates` class with Haversine distance calculation
- `Location` dataclass with tier system
- `LocationDatabase` with 18 pre-loaded major cities
- `LocationPreference` for user settings

✅ **Integration** - Router registered in `main.py`

### Frontend (React/TypeScript)

✅ **useGeolocation Hook** (`fronto/src/hooks/useGeolocation.ts`)
- Auto-detection with browser geolocation
- Nearest city finding
- Nearby cities within radius
- Distance calculations
- User preference management
- Event filtering by location
- Location caching

✅ **Existing Utilities** (`fronto/src/utils/geolocation.ts`)
- Browser geolocation API wrapper
- localStorage management
- API integration functions

## Quick Start

### 1. Test the Location API

```bash
# Get major cities
curl http://localhost:8000/api/locations/major-cities

# Find nearest to NYC
curl -X POST http://localhost:8000/api/locations/nearest-cities \
  -H "Content-Type: application/json" \
  -d '{"latitude": 40.7128, "longitude": -74.0060, "limit": 5}'

# Get cities within 100 miles of LA
curl -X POST http://localhost:8000/api/locations/nearby \
  -H "Content-Type: application/json" \
  -d '{"latitude": 34.0522, "longitude": -118.2437, "radius_miles": 100}'

# Search for cities
curl "http://localhost:8000/api/locations/search?q=los+angeles"

# Get location stats
curl http://localhost:8000/api/locations/stats
```

### 2. Use the Geolocation Hook

```tsx
import { useGeolocation } from '@/hooks/useGeolocation';

function EventDiscovery() {
  const {
    userLocation,
    nearestCity,
    nearbyCities,
    selectedCity,
    isDetecting,
    error,
    detectLocation,
    selectCity,
    getEventsNearby,
    calculateDistance
  } = useGeolocation({
    autoDetect: true,
    preferredRadius: 25,
    onLocationChange: (cityCode) => {
      console.log('User selected:', cityCode);
    }
  });

  // Auto-detect runs on mount
  // Or manually trigger:
  // <button onClick={detectLocation}>Find My Location</button>

  return (
    <div>
      {isDetecting && <p>Detecting your location...</p>}
      {nearestCity && (
        <p>Nearest city: {nearestCity.name} ({nearestCity.distance_miles} miles)</p>
      )}
      
      {/* Show nearby cities */}
      <h3>Cities within 25 miles:</h3>
      {nearbyCities.map(city => (
        <button key={city.code} onClick={() => selectCity(city.code)}>
          {city.name} ({city.distance_miles} miles)
        </button>
      ))}
    </div>
  );
}
```

### 3. Advanced: Events by Proximity

```tsx
function NearbyEvents() {
  const { userLocation, getEventsNearby, isNearby } = useGeolocation();
  const [events, setEvents] = useState([]);

  useEffect(() => {
    if (userLocation) {
      // Get events within 25 miles
      getEventsNearby(25).then(setEvents);
    }
  }, [userLocation]);

  return (
    <div>
      <h2>Events Near You</h2>
      {events.map(event => (
        <EventCard 
          key={event.id} 
          event={event}
          distance={event.distance_miles}
        />
      ))}
    </div>
  );
}
```

## API Endpoints Reference

### Discovery

#### GET `/api/locations/major-cities`
Get all major cities with optional filtering.

**Query Parameters:**
- `sort_by`: `name`, `population`, or `distance_from`
- `country`: Filter by country code (US, CA, etc.)
- `lat`, `lon`: Coordinates for distance sorting
- `limit`: Max results (default: 50)

**Response:**
```json
{
  "success": true,
  "count": 18,
  "cities": [
    {
      "code": "ca--los-angeles",
      "name": "Los Angeles, CA",
      "tier": "major",
      "coordinates": {"latitude": 34.0522, "longitude": -118.2437},
      "state": "CA",
      "country": "US",
      "population": 3979576,
      "timezone": "America/Los_Angeles"
    }
  ]
}
```

### Geolocation

#### POST `/api/locations/nearest-cities`
Find nearest cities to coordinates.

**Request:**
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
  "center": {"latitude": 40.7128, "longitude": -74.0060},
  "results": [
    {
      "location": {...},
      "distance_miles": 0.0
    }
  ]
}
```

#### POST `/api/locations/nearby`
Get locations within specified radius.

**Request:**
```json
{
  "latitude": 34.0522,
  "longitude": -118.2437,
  "radius_miles": 50.0,
  "tier": "major"
}
```

### Events by Location

#### GET `/api/locations/events/nearby`
Get events within radius of coordinates.

**Query Parameters:**
- `lat`: Latitude (required)
- `lon`: Longitude (required)
- `radius_miles`: Search radius (default: 25)
- `limit`: Max events (default: 100)

**Response:**
```json
{
  "success": true,
  "center": {"latitude": 34.0522, "longitude": -118.2437},
  "radius_miles": 25,
  "count": 42,
  "events": [
    {
      "id": 1,
      "title": "Underground Rave",
      "date": "2026-02-15",
      "location": "Downtown LA",
      "city": "ca--los-angeles",
      "distance_miles": 3.2
    }
  ]
}
```

#### GET `/api/locations/events/by-city/{city_code}`
Get events for a specific city.

**Query Parameters:**
- `include_nearby`: Include events from nearby cities (default: false)
- `radius_miles`: Radius for nearby cities (default: 25)

### User Preferences

#### POST `/api/locations/preferences`
Save user's location preference.

**Request:**
```json
{
  "user_id": "user_123",
  "major_city_code": "ca--los-angeles",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "auto_detect": true,
  "preferred_radius": 25
}
```

#### GET `/api/locations/preferences/{user_id}`
Retrieve saved preference.

### Search

#### GET `/api/locations/search`
Search locations by name.

**Query Parameters:**
- `q`: Search query (min 2 chars, required)
- `tier`: Filter by tier
- `country`: Filter by country
- `limit`: Max results (default: 20)

**Example:**
```bash
curl "http://localhost:8000/api/locations/search?q=angeles&country=US"
```

## useGeolocation Hook API

### Options

```typescript
interface UseGeolocationOptions {
  autoDetect?: boolean;      // Auto-detect on mount (default: true)
  preferredRadius?: number;  // Default radius in miles (default: 25)
  onLocationChange?: (cityCode: string) => void;  // Callback when city changes
}
```

### Return Values

```typescript
interface UseGeolocationReturn {
  // State
  userLocation: Coordinates | null;      // User's coordinates
  nearestCity: LocationData | null;      // Closest major city
  nearbyCities: LocationData[];          // Cities within radius
  selectedCity: string | null;           // Currently selected city code
  isDetecting: boolean;                  // Detection in progress
  error: string | null;                  // Error message
  
  // Actions
  detectLocation: () => Promise<void>;   // Trigger detection
  selectCity: (cityCode: string) => void; // Manually select city
  findNearestCity: (coords: Coordinates) => Promise<LocationData | null>;
  getNearbyCities: (coords: Coordinates, radius?: number) => Promise<LocationData[]>;
  getEventsNearby: (radius?: number) => Promise<any[]>;
  savePreference: (preference: Partial<LocationPreference>) => Promise<void>;
  loadPreference: () => LocationPreference | null;
  
  // Utilities
  calculateDistance: (lat1, lon1, lat2, lon2) => number; // Haversine formula
  isNearby: (cityCode: string, maxDistance?: number) => boolean;
}
```

### Usage Examples

#### Basic Auto-Detection

```tsx
function App() {
  const { nearestCity, isDetecting, error } = useGeolocation();

  if (isDetecting) return <p>Finding your location...</p>;
  if (error) return <p>Error: {error}</p>;
  
  return (
    <div>
      <h1>Welcome to {nearestCity?.name || 'InYacity'}</h1>
    </div>
  );
}
```

#### Manual City Selection

```tsx
function CityPicker() {
  const { selectCity, nearbyCities, selectedCity } = useGeolocation();

  return (
    <div>
      <h3>Select a city:</h3>
      {nearbyCities.map(city => (
        <button
          key={city.code}
          onClick={() => selectCity(city.code)}
          className={selectedCity === city.code ? 'active' : ''}
        >
          {city.name} ({city.distance_miles} miles away)
        </button>
      ))}
    </div>
  );
}
```

#### Events Within Radius

```tsx
function ProximityEvents() {
  const { userLocation, getEventsNearby, calculateDistance } = useGeolocation();
  const [radius, setRadius] = useState(25);
  const [events, setEvents] = useState([]);

  const loadEvents = async () => {
    const nearbyEvents = await getEventsNearby(radius);
    setEvents(nearbyEvents);
  };

  return (
    <div>
      <label>
        Search radius: {radius} miles
        <input
          type="range"
          min="5"
          max="100"
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
        />
      </label>
      <button onClick={loadEvents}>Find Events</button>
      
      {events.map(event => (
        <div key={event.id}>
          <h4>{event.title}</h4>
          <p>{event.distance_miles} miles away</p>
        </div>
      ))}
    </div>
  );
}
```

#### Save User Preference

```tsx
function LocationSettings() {
  const { savePreference, loadPreference, selectedCity } = useGeolocation();
  const [autoDetect, setAutoDetect] = useState(true);
  const [radius, setRadius] = useState(25);

  const handleSave = () => {
    savePreference({
      major_city_code: selectedCity,
      auto_detect: autoDetect,
      preferred_radius: radius
    });
  };

  return (
    <div>
      <label>
        <input
          type="checkbox"
          checked={autoDetect}
          onChange={(e) => setAutoDetect(e.target.checked)}
        />
        Auto-detect my location
      </label>
      
      <label>
        Preferred search radius: {radius} miles
        <input
          type="range"
          min="5"
          max="100"
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
        />
      </label>
      
      <button onClick={handleSave}>Save Preferences</button>
    </div>
  );
}
```

## Integration with CitySelector

The `CitySelector` component can now use the advanced geolocation features:

```tsx
import { useGeolocation } from '@/hooks/useGeolocation';

function EnhancedCitySelector() {
  const {
    nearestCity,
    nearbyCities,
    isDetecting,
    detectLocation,
    selectCity
  } = useGeolocation({
    autoDetect: true,
    onLocationChange: (cityCode) => {
      // Auto-scroll to city or show events
      console.log('Location changed to:', cityCode);
    }
  });

  return (
    <div>
      {/* Auto-detect button */}
      <button onClick={detectLocation} disabled={isDetecting}>
        {isDetecting ? 'Detecting...' : '📍 Use My Location'}
      </button>

      {/* Show nearest city */}
      {nearestCity && (
        <div className="nearest-city">
          <h3>Nearest to you:</h3>
          <button onClick={() => selectCity(nearestCity.code)}>
            {nearestCity.name} ({nearestCity.distance_miles} miles)
          </button>
        </div>
      )}

      {/* Show nearby cities */}
      <h3>Cities within 25 miles:</h3>
      <div className="nearby-cities">
        {nearbyCities.map(city => (
          <CityCard
            key={city.code}
            city={city}
            onClick={() => selectCity(city.code)}
          />
        ))}
      </div>

      {/* Show all cities with distance */}
      <h3>All Cities:</h3>
      <CityList />
    </div>
  );
}
```

## Distance Calculation

The system uses the Haversine formula for accurate distance calculations:

```typescript
// Calculate distance between two points
const distance = calculateDistance(
  34.0522, -118.2437,  // LA
  40.7128, -74.0060    // NYC
);
console.log(distance); // ~2445 miles
```

## Caching Strategy

The system implements multiple caching layers:

1. **Browser Cache** (24 hours)
   - User coordinates stored in localStorage
   - Avoids repeated geolocation permission requests

2. **API Response Cache** (in-memory)
   - Nearest cities results
   - Nearby locations within radius
   - Refreshes on page reload

3. **User Preferences** (persistent)
   - Selected city
   - Auto-detect setting
   - Preferred radius

## Security Considerations

- HTTPS required for browser geolocation (except localhost)
- User must grant permission for location access
- Coordinates are never stored on server without explicit user action
- Location data is cached locally only

## Error Handling

The system gracefully handles:

- Browser doesn't support geolocation
- User denies location permission
- Network errors during API calls
- Invalid coordinates
- GPS timeout

```tsx
const { error, detectLocation } = useGeolocation();

if (error) {
  return (
    <div>
      <p>Could not detect location: {error}</p>
      <button onClick={detectLocation}>Try Again</button>
      <p>Or select a city manually:</p>
      <CityList />
    </div>
  );
}
```

## Performance Optimization

- Distance calculations use efficient Haversine formula
- API calls are cached to prevent duplicate requests
- Geolocation is requested only once per session
- Coordinates cached for 24 hours
- Batch API calls when possible

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Full support
- IE11: Not supported (no geolocation API)

## Testing

```bash
# Test API endpoints
curl http://localhost:8000/api/locations/health

# Test with coordinates
curl -X POST http://localhost:8000/api/locations/nearest-cities \
  -H "Content-Type: application/json" \
  -d '{"latitude": 34.0522, "longitude": -118.2437, "limit": 3}'

# Test events by location
curl "http://localhost:8000/api/locations/events/nearby?lat=34.0522&lon=-118.2437&radius_miles=50"
```

## Future Enhancements

- [ ] IP-based geolocation fallback
- [ ] Real-time location tracking (with user consent)
- [ ] Location-based push notifications
- [ ] Heatmaps of event density
- [ ] Commute time estimation (integrate with Google Maps API)
- [ ] Location sharing between users

## Troubleshooting

### "Geolocation not supported"
- Ensure you're on HTTPS (or localhost)
- Check browser version (IE11 not supported)

### "User denied permission"
- Clear browser permissions for the site
- Check OS-level location settings
- Use manual city selection as fallback

### "Distance calculations seem wrong"
- Verify coordinates are correct (WGS84 format)
- Check for negative longitude in Western hemisphere
- Haversine formula gives straight-line distance (not driving distance)

## Support

For issues:
1. Check browser console for errors
2. Verify API endpoints are accessible
3. Test geolocation permission in browser settings
4. Check that backend router is registered

Part of the Nocturne Event Platform.
