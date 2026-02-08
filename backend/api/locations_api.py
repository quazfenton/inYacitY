"""
Location API Endpoints

RESTful API for:
- Geolocation detection
- City discovery
- Proximity-based queries
- User location preferences
- Event filtering by location
"""

from flask import Blueprint, request, jsonify
from typing import Optional
from datetime import datetime
import json

from models.locations import (
    Coordinates, Location, LocationPreference, LocationDatabase,
    LocationTier
)

# Initialize location database (singleton)
location_db = LocationDatabase()

# Create Blueprint
locations_bp = Blueprint('locations', __name__, url_prefix='/api/locations')


# ============================================================================
# DISCOVERY ENDPOINTS
# ============================================================================

@locations_bp.route('/major-cities', methods=['GET'])
def get_major_cities():
    """
    Get all major cities
    
    Query Parameters:
        - sort_by: 'name', 'population', or 'distance_from' (requires lat/lon)
        - country: Filter by country code (e.g., 'US', 'CA')
        - limit: Max results (default: 50)
    Returns:
        List of major cities with coordinates and metadata
    """
    try:
        major_cities = location_db.get_major_cities()
        
        # Filter by country if specified
        country = request.args.get('country')
        if country:
            major_cities = [c for c in major_cities if c.country == country.upper()]
        
        # Sort options
        sort_by = request.args.get('sort_by', 'name')
        if sort_by == 'population':
            major_cities = sorted(major_cities, key=lambda x: x.population or 0, reverse=True)
        elif sort_by == 'distance_from':
            # Calculate distance from provided coordinates
            lat = request.args.get('lat', type=float)
            lon = request.args.get('lon', type=float)
            if lat is not None and lon is not None:
                user_coords = Coordinates(lat, lon)
                major_cities = sorted(
                    major_cities,
                    key=lambda x: user_coords.distance_to(x.coordinates)
                )
        
        # Limit results
        limit = request.args.get('limit', 50, type=int)
        major_cities = major_cities[:limit]
        
        return jsonify({
            'success': True,
            'count': len(major_cities),
            'cities': [city.to_dict() for city in major_cities]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@locations_bp.route('/location/<code>', methods=['GET'])
def get_location(code: str):
    """
    Get location details by code
    
    Args:
        code: Location code (e.g., 'ca--los-angeles')
    
    Returns:
        Location details including coordinates and metadata
    """
    try:
        location = location_db.get_location(code)
        
        if not location:
            return jsonify({
                'success': False,
                'error': f'Location {code} not found'
            }), 404
        
        response = location.to_dict()
        
        # Include secondary cities if it's a major city
        if location.tier == LocationTier.MAJOR_CITY:
            secondary = location_db.get_secondary_cities(code)
            response['secondary_cities'] = [city.to_dict() for city in secondary]
        
        return jsonify({
            'success': True,
            'location': response
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# GEOLOCATION ENDPOINTS
# ============================================================================

@locations_bp.route('/nearest-cities', methods=['POST'])
def get_nearest_cities():
    """
    Find nearest major cities to given coordinates
    
    Request Body:
        {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "limit": 5
        }
    
    Returns:
        List of nearest cities with distances in miles
    """
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({
                'success': False,
                'error': 'latitude and longitude required'
            }), 400
        
        user_coords = Coordinates(
            latitude=float(data['latitude']),
            longitude=float(data['longitude'])
        )
        
        limit = data.get('limit', 5)
        nearest = location_db.find_nearest_city(user_coords, limit=limit)
        
        results = [
            {
                'location': city.to_dict(),
                'distance_miles': round(dist, 2)
            }
            for city, dist in nearest
        ]
        
        return jsonify({
            'success': True,
            'center': {
                'latitude': data['latitude'],
                'longitude': data['longitude']
            },
            'results': results,
            'count': len(results)
        }), 200
        
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': 'Invalid coordinates'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@locations_bp.route('/nearby', methods=['POST'])
def get_nearby_locations():
    """
    Get all locations within specified radius
    
    Request Body:
        {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius_miles": 25.0,
            "tier": "major"  // optional: filter by tier
        }
    
    Returns:
        List of locations within radius, sorted by distance
    """
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({
                'success': False,
                'error': 'latitude and longitude required'
            }), 400
        
        user_coords = Coordinates(
            latitude=float(data['latitude']),
            longitude=float(data['longitude'])
        )
        
        radius = data.get('radius_miles', 25.0)
        nearby = location_db.get_nearby_locations(user_coords, radius)
        
        # Filter by tier if specified
        tier = data.get('tier')
        if tier:
            nearby = [(loc, dist) for loc, dist in nearby if loc.tier.value == tier]
        
        results = [
            {
                'location': city.to_dict(),
                'distance_miles': round(dist, 2)
            }
            for city, dist in nearby
        ]
        
        return jsonify({
            'success': True,
            'center': {
                'latitude': data['latitude'],
                'longitude': data['longitude']
            },
            'radius_miles': radius,
            'results': results,
            'count': len(results)
        }), 200
        
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': 'Invalid coordinates'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# USER PREFERENCE ENDPOINTS
# ============================================================================

@locations_bp.route('/preferences', methods=['POST'])
def set_location_preference():
    """
    Set user's location preference
    
    Request Body:
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
    
    Response: Preference saved confirmation
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'major_city_code' not in data:
            return jsonify({
                'success': False,
                'error': 'user_id and major_city_code required'
            }), 400
        
        # Validate city exists
        city = location_db.get_location(data['major_city_code'])
        if not city:
            return jsonify({
                'success': False,
                'error': f"City {data['major_city_code']} not found"
            }), 404
        
        secondary_loc = None
        if 'secondary_location' in data and data['secondary_location']:
            secondary_loc = Coordinates(
                latitude=float(data['secondary_location']['latitude']),
                longitude=float(data['secondary_location']['longitude'])
            )
        
        preference = LocationPreference(
            user_id=data['user_id'],
            major_city_code=data['major_city_code'],
            secondary_location=secondary_loc,
            auto_detect=data.get('auto_detect', True),
            preferred_radius=float(data.get('preferred_radius', 25.0)),
            stored_at=datetime.utcnow().isoformat()
        )
        
        # TODO: Persist to database (implementation depends on backend choice)
        # preferences_db.save(preference)
        
        return jsonify({
            'success': True,
            'message': 'Location preference saved',
            'preference': preference.to_dict()
        }), 201
        
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': 'Invalid preference data'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@locations_bp.route('/preferences/<user_id>', methods=['GET'])
def get_location_preference(user_id: str):
    """
    Get user's saved location preference
    
    Args:
        user_id: User identifier
    
    Returns:
        User's location preference
    """
    try:
        # TODO: Retrieve from database
        # preference = preferences_db.get(user_id)
        
        return jsonify({
            'success': True,
            'message': 'Location preference retrieved'
            # 'preference': preference.to_dict() if preference else None
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SEARCH & FILTER ENDPOINTS
# ============================================================================

@locations_bp.route('/search', methods=['GET'])
def search_locations():
    """
    Search locations by name or code
    
    Query Parameters:
        - q: Search query (matches name or code)
        - tier: Filter by location tier
        - country: Filter by country
        - limit: Max results (default: 20)
    
    Returns:
        List of matching locations
    """
    try:
        query = request.args.get('q', '').lower()
        
        if not query or len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Query must be at least 2 characters'
            }), 400
        
        # Search through locations
        matches = []
        for loc in location_db.locations.values():
            if query in loc.name.lower() or query in loc.code.lower():
                matches.append(loc)
        
        # Filter by tier if specified
        tier = request.args.get('tier')
        if tier:
            matches = [l for l in matches if l.tier.value == tier]
        
        # Filter by country if specified
        country = request.args.get('country')
        if country:
            matches = [l for l in matches if l.country == country.upper()]
        
        # Sort by match quality
        matches = sorted(
            matches,
            key=lambda x: (
                x.name.lower().startswith(query),  # Exact prefix match first
                x.name.lower().count(query),        # Multiple matches higher
                x.name
            ),
            reverse=True
        )
        
        # Limit results
        limit = request.args.get('limit', 20, type=int)
        matches = matches[:limit]
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(matches),
            'results': [loc.to_dict() for loc in matches]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@locations_bp.route('/stats', methods=['GET'])
def get_location_stats():
    """
    Get location database statistics
    
    Returns:
        Count of major cities, secondary cities, etc.
    """
    try:
        return jsonify({
            'success': True,
            'stats': {
                'total_locations': len(location_db.locations),
                'major_cities': len(location_db.major_cities),
                'secondary_cities': len(location_db.secondary_cities),
                'countries': len(set(loc.country for loc in location_db.locations.values())),
                'populated_by_tier': {
                    'major': len([l for l in location_db.locations.values() if l.tier == LocationTier.MAJOR_CITY]),
                    'secondary': len([l for l in location_db.locations.values() if l.tier == LocationTier.SECONDARY_CITY]),
                    'town': len([l for l in location_db.locations.values() if l.tier == LocationTier.TOWN]),
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@locations_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database_loaded': len(location_db.locations) > 0
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@locations_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request"""
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': str(error)
    }), 400


@locations_bp.errorhandler(404)
def not_found(error):
    """Handle not found"""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': str(error)
    }), 404


@locations_bp.errorhandler(500)
def internal_error(error):
    """Handle internal error"""
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': str(error)
    }), 500
