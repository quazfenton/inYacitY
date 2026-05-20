"""
Location and Geolocation Data Models

Provides hierarchical location structure with:
- Major cities (tier 1)
- Secondary cities/towns (tier 2)
- Coordinates (lat/long)
- Distance calculations
- Proximity-based queries
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum
import math


class LocationTier(Enum):
    """Location hierarchy tiers"""
    MAJOR_CITY = "major"
    SECONDARY_CITY = "secondary"
    TOWN = "town"
    REGION = "region"


@dataclass
class Coordinates:
    """Geographic coordinates"""
    latitude: float
    longitude: float

    def distance_to(self, other: 'Coordinates') -> float:
        """
        Calculate distance to another coordinate in miles (Haversine formula)
        
        Args:
            other: Another Coordinates object
            
        Returns:
            Distance in miles
        """
        R = 3959  # Earth's radius in miles
        
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude
        }

    @staticmethod
    def from_dict(data: dict) -> 'Coordinates':
        """Deserialize from dictionary"""
        return Coordinates(data['latitude'], data['longitude'])


@dataclass
class Location:
    """
    Represents a geographic location
    
    Attributes:
        id: Unique identifier
        code: City code (e.g., 'ca--los-angeles')
        name: Display name
        tier: Location tier (major, secondary, town)
        coordinates: Lat/long coordinates
        state: State/province abbreviation
        country: Country code
        population: Population (optional)
        parent_city: Parent major city code (for secondary cities)
        metadata: Additional data
    """
    id: str
    code: str
    name: str
    tier: LocationTier
    coordinates: Coordinates
    state: str
    country: str
    population: Optional[int] = None
    parent_city: Optional[str] = None  # Reference to major city
    timezone: Optional[str] = None
    metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'tier': self.tier.value,
            'coordinates': self.coordinates.to_dict(),
            'state': self.state,
            'country': self.country,
            'population': self.population,
            'parent_city': self.parent_city,
            'timezone': self.timezone,
            'metadata': self.metadata or {}
        }

    @staticmethod
    def from_dict(data: dict) -> 'Location':
        """Deserialize from dictionary"""
        return Location(
            id=data['id'],
            code=data['code'],
            name=data['name'],
            tier=LocationTier(data['tier']),
            coordinates=Coordinates.from_dict(data['coordinates']),
            state=data['state'],
            country=data['country'],
            population=data.get('population'),
            parent_city=data.get('parent_city'),
            timezone=data.get('timezone'),
            metadata=data.get('metadata', {})
        )


@dataclass
class LocationPreference:
    """
    User's location preference/profile
    
    Attributes:
        user_id: User identifier
        major_city_code: Primary city code
        secondary_location: Fine-grained location (lat/long or secondary city)
        auto_detect: Whether to auto-detect location
        preferred_radius: Preferred search radius in miles
        stored_at: When preference was stored
    """
    user_id: str
    major_city_code: str
    secondary_location: Optional[Coordinates] = None
    auto_detect: bool = True
    preferred_radius: float = 25.0  # Default 25 mile radius
    stored_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            'user_id': self.user_id,
            'major_city_code': self.major_city_code,
            'secondary_location': self.secondary_location.to_dict() if self.secondary_location else None,
            'auto_detect': self.auto_detect,
            'preferred_radius': self.preferred_radius,
            'stored_at': self.stored_at
        }


class LocationDatabase:
    """
    In-memory location database with hierarchical structure
    
    Includes:
    - Major cities with coordinates
    - Secondary cities/towns with parent city references
    - Distance calculations
    - Proximity queries
    """

    def __init__(self):
        """Initialize location database"""
        self.locations: dict[str, Location] = {}
        self.major_cities: dict[str, Location] = {}
        self.secondary_cities: dict[str, Location] = {}
        self._initialize_default_locations()

    def _initialize_default_locations(self):
        """Load default major and secondary cities"""
        
        # MAJOR CITIES (from scraper config)
        major_cities_data = [
            # California
            {
                'code': 'ca--los-angeles',
                'name': 'Los Angeles, CA',
                'coords': Coordinates(34.0522, -118.2437),
                'state': 'CA',
                'country': 'US',
                'population': 3979576,
                'timezone': 'America/Los_Angeles'
            },
            {
                'code': 'ca--san-francisco',
                'name': 'San Francisco, CA',
                'coords': Coordinates(37.7749, -122.4194),
                'state': 'CA',
                'country': 'US',
                'population': 873965,
                'timezone': 'America/Los_Angeles'
            },
            {
                'code': 'ca--san-diego',
                'name': 'San Diego, CA',
                'coords': Coordinates(32.7157, -117.1611),
                'state': 'CA',
                'country': 'US',
                'population': 1423851,
                'timezone': 'America/Los_Angeles'
            },
            
            # Colorado
            {
                'code': 'co--denver',
                'name': 'Denver, CO',
                'coords': Coordinates(39.7392, -104.9903),
                'state': 'CO',
                'country': 'US',
                'population': 727211,
                'timezone': 'America/Denver'
            },
            
            # Washington, D.C.
            {
                'code': 'dc--washington',
                'name': 'Washington, DC',
                'coords': Coordinates(38.9072, -77.0369),
                'state': 'DC',
                'country': 'US',
                'population': 705749,
                'timezone': 'America/New_York'
            },
            
            # Florida
            {
                'code': 'fl--miami',
                'name': 'Miami, FL',
                'coords': Coordinates(25.7617, -80.1918),
                'state': 'FL',
                'country': 'US',
                'population': 442241,
                'timezone': 'America/New_York'
            },
            
            # Georgia
            {
                'code': 'ga--atlanta',
                'name': 'Atlanta, GA',
                'coords': Coordinates(33.7490, -84.3880),
                'state': 'GA',
                'country': 'US',
                'population': 498044,
                'timezone': 'America/New_York'
            },
            
            # Illinois
            {
                'code': 'il--chicago',
                'name': 'Chicago, IL',
                'coords': Coordinates(41.8781, -87.6298),
                'state': 'IL',
                'country': 'US',
                'population': 2693976,
                'timezone': 'America/Chicago'
            },
            
            # Massachusetts
            {
                'code': 'ma--boston',
                'name': 'Boston, MA',
                'coords': Coordinates(42.3601, -71.0589),
                'state': 'MA',
                'country': 'US',
                'population': 692600,
                'timezone': 'America/New_York'
            },
            
            # Nevada
            {
                'code': 'nv--las-vegas',
                'name': 'Las Vegas, NV',
                'coords': Coordinates(36.1699, -115.1398),
                'state': 'NV',
                'country': 'US',
                'population': 644018,
                'timezone': 'America/Los_Angeles'
            },
            
            # New York
            {
                'code': 'ny--new-york',
                'name': 'New York, NY',
                'coords': Coordinates(40.7128, -74.0060),
                'state': 'NY',
                'country': 'US',
                'population': 8398748,
                'timezone': 'America/New_York'
            },
            
            # Pennsylvania
            {
                'code': 'pa--philadelphia',
                'name': 'Philadelphia, PA',
                'coords': Coordinates(39.9526, -75.1652),
                'state': 'PA',
                'country': 'US',
                'population': 1602494,
                'timezone': 'America/New_York'
            },
            
            # Texas
            {
                'code': 'tx--austin',
                'name': 'Austin, TX',
                'coords': Coordinates(30.2672, -97.7431),
                'state': 'TX',
                'country': 'US',
                'population': 961855,
                'timezone': 'America/Chicago'
            },
            {
                'code': 'tx--dallas',
                'name': 'Dallas, TX',
                'coords': Coordinates(32.7767, -96.7970),
                'state': 'TX',
                'country': 'US',
                'population': 1304379,
                'timezone': 'America/Chicago'
            },
            {
                'code': 'tx--houston',
                'name': 'Houston, TX',
                'coords': Coordinates(29.7604, -95.3698),
                'state': 'TX',
                'country': 'US',
                'population': 2320268,
                'timezone': 'America/Chicago'
            },
            
            # Utah
            {
                'code': 'ut--salt-lake-city',
                'name': 'Salt Lake City, UT',
                'coords': Coordinates(40.7608, -111.8910),
                'state': 'UT',
                'country': 'US',
                'population': 199723,
                'timezone': 'America/Denver'
            },
            
            # Washington
            {
                'code': 'wa--seattle',
                'name': 'Seattle, WA',
                'coords': Coordinates(47.6062, -122.3321),
                'state': 'WA',
                'country': 'US',
                'population': 753675,
                'timezone': 'America/Los_Angeles'
            },
            
            # Canada
            {
                'code': 'on--toronto',
                'name': 'Toronto, ON',
                'coords': Coordinates(43.6532, -79.3832),
                'state': 'ON',
                'country': 'CA',
                'population': 2930000,
                'timezone': 'America/Toronto'
            },
        ]

        for data in major_cities_data:
            location = Location(
                id=data['code'],
                code=data['code'],
                name=data['name'],
                tier=LocationTier.MAJOR_CITY,
                coordinates=data['coords'],
                state=data['state'],
                country=data['country'],
                population=data['population'],
                timezone=data['timezone']
            )
            self.add_location(location)

    def add_location(self, location: Location) -> None:
        """Add a location to the database"""
        self.locations[location.code] = location
        
        if location.tier == LocationTier.MAJOR_CITY:
            self.major_cities[location.code] = location
        elif location.tier == LocationTier.SECONDARY_CITY:
            self.secondary_cities[location.code] = location

    def get_location(self, code: str) -> Optional[Location]:
        """Get location by code"""
        return self.locations.get(code)

    def get_major_cities(self) -> List[Location]:
        """Get all major cities sorted by name"""
        return sorted(self.major_cities.values(), key=lambda x: x.name)

    def get_secondary_cities(self, parent_city_code: str) -> List[Location]:
        """Get secondary cities for a major city"""
        return [
            loc for loc in self.secondary_cities.values()
            if loc.parent_city == parent_city_code
        ]

    def find_nearest_city(self, coordinates: Coordinates, limit: int = 5) -> List[Tuple[Location, float]]:
        """
        Find nearest major cities to coordinates
        
        Args:
            coordinates: User's coordinates
            limit: Maximum number of results
            
        Returns:
            List of (Location, distance_in_miles) tuples
        """
        distances = []
        for city in self.major_cities.values():
            dist = coordinates.distance_to(city.coordinates)
            distances.append((city, dist))
        
        return sorted(distances, key=lambda x: x[1])[:limit]

    def get_nearby_locations(
        self,
        center: Coordinates,
        radius_miles: float = 25.0
    ) -> List[Tuple[Location, float]]:
        """
        Get all locations within radius
        
        Args:
            center: Center coordinates
            radius_miles: Search radius
            
        Returns:
            List of (Location, distance_in_miles) tuples
        """
        nearby = []
        for location in self.locations.values():
            dist = center.distance_to(location.coordinates)
            if dist <= radius_miles:
                nearby.append((location, dist))
        
        return sorted(nearby, key=lambda x: x[1])
