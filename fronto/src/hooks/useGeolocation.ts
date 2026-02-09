/**
 * Advanced Geolocation Hook
 * 
 * Provides:
 * - Auto-detection with browser geolocation
 * - Nearest city finding
 * - Location-based event filtering
 * - Distance calculations
 * - User preference management
 * - Real-time location updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface Coordinates {
  latitude: number;
  longitude: number;
}

interface LocationData {
  code: string;
  name: string;
  coordinates: Coordinates;
  distance_miles?: number;
}

interface LocationPreference {
  major_city_code: string;
  secondary_location?: Coordinates;
  auto_detect: boolean;
  preferred_radius: number;
  stored_at: string;
}

interface UseGeolocationOptions {
  autoDetect?: boolean;
  preferredRadius?: number;
  onLocationChange?: (cityCode: string) => void;
}

interface UseGeolocationReturn {
  // State
  userLocation: Coordinates | null;
  nearestCity: LocationData | null;
  nearbyCities: LocationData[];
  selectedCity: string | null;
  isDetecting: boolean;
  error: string | null;
  
  // Actions
  detectLocation: () => Promise<void>;
  selectCity: (cityCode: string) => void;
  findNearestCity: (coords: Coordinates) => Promise<LocationData | null>;
  getNearbyCities: (coords: Coordinates, radius?: number) => Promise<LocationData[]>;
  getEventsNearby: (radius?: number) => Promise<any[]>;
  savePreference: (preference: Partial<LocationPreference>) => Promise<void>;
  loadPreference: () => LocationPreference | null;
  
  // Utilities
  calculateDistance: (lat1: number, lon1: number, lat2: number, lon2: number) => number;
  isNearby: (cityCode: string, maxDistance?: number) => boolean;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const LOCATION_CACHE_KEY = 'inyacity_location_cache';
const LOCATION_PREF_KEY = 'inyacity_location_preference';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

export function useGeolocation(options: UseGeolocationOptions = {}): UseGeolocationReturn {
  const { autoDetect = true, preferredRadius = 25, onLocationChange } = options;
  
  // State
  const [userLocation, setUserLocation] = useState<Coordinates | null>(null);
  const [nearestCity, setNearestCity] = useState<LocationData | null>(null);
  const [nearbyCities, setNearbyCities] = useState<LocationData[]>([]);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const locationCache = useRef<Map<string, any>>(new Map());
  
  /**
   * Calculate distance between two coordinates using Haversine formula
   */
  const calculateDistance = useCallback((lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 3959; // Earth's radius in miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }, []);
  
  /**
   * Detect user location using browser geolocation API
   */
  const detectLocation = useCallback(async () => {
    setIsDetecting(true);
    setError(null);
    
    try {
      // Check cache first
      const cached = getCachedLocation();
      if (cached) {
        setUserLocation(cached);
        const nearest = await findNearestCity(cached);
        if (nearest) {
          setNearestCity(nearest);
          setSelectedCity(nearest.code);
          onLocationChange?.(nearest.code);
        }
        setIsDetecting(false);
        return;
      }
      
      // Request browser geolocation
      if (!navigator.geolocation) {
        throw new Error('Geolocation not supported by browser');
      }
      
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: false,
          timeout: 10000,
          maximumAge: 60000
        });
      });
      
      const coords: Coordinates = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      };
      
      setUserLocation(coords);
      cacheLocation(coords);
      
      // Find nearest city
      const nearest = await findNearestCity(coords);
      if (nearest) {
        setNearestCity(nearest);
        setSelectedCity(nearest.code);
        onLocationChange?.(nearest.code);
      }
      
      // Get nearby cities
      const nearby = await getNearbyCities(coords, preferredRadius);
      setNearbyCities(nearby);
      
    } catch (err: any) {
      console.error('Geolocation error:', err);
      setError(err.message || 'Failed to detect location');
      
      // Try to load saved preference as fallback
      const saved = loadPreference();
      if (saved) {
        setSelectedCity(saved.major_city_code);
        onLocationChange?.(saved.major_city_code);
      }
    } finally {
      setIsDetecting(false);
    }
  }, [preferredRadius, onLocationChange]);
  
  /**
   * Find nearest city to coordinates
   */
  const findNearestCity = useCallback(async (coords: Coordinates): Promise<LocationData | null> => {
    try {
      const cacheKey = `nearest-${coords.latitude}-${coords.longitude}`;
      if (locationCache.current.has(cacheKey)) {
        return locationCache.current.get(cacheKey);
      }
      
      const response = await fetch(`${API_BASE_URL}/api/locations/nearest-cities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: coords.latitude,
          longitude: coords.longitude,
          limit: 1
        })
      });
      
      if (!response.ok) throw new Error('Failed to find nearest city');
      
      const data = await response.json();
      if (data.success && data.results.length > 0) {
        const result = data.results[0];
        locationCache.current.set(cacheKey, result);
        return result;
      }
      
      return null;
    } catch (err) {
      console.error('Error finding nearest city:', err);
      return null;
    }
  }, []);
  
  /**
   * Get nearby cities within radius
   */
  const getNearbyCities = useCallback(async (
    coords: Coordinates, 
    radius: number = preferredRadius
  ): Promise<LocationData[]> => {
    try {
      const cacheKey = `nearby-${coords.latitude}-${coords.longitude}-${radius}`;
      if (locationCache.current.has(cacheKey)) {
        return locationCache.current.get(cacheKey);
      }
      
      const response = await fetch(`${API_BASE_URL}/api/locations/nearby`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: coords.latitude,
          longitude: coords.longitude,
          radius_miles: radius
        })
      });
      
      if (!response.ok) throw new Error('Failed to get nearby cities');
      
      const data = await response.json();
      if (data.success) {
        locationCache.current.set(cacheKey, data.results);
        return data.results;
      }
      
      return [];
    } catch (err) {
      console.error('Error getting nearby cities:', err);
      return [];
    }
  }, [preferredRadius]);
  
  /**
   * Get events near user location
   */
  const getEventsNearby = useCallback(async (radius: number = preferredRadius): Promise<any[]> => {
    if (!userLocation) {
      throw new Error('User location not available');
    }
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/locations/events/nearby?` +
        `lat=${userLocation.latitude}&lon=${userLocation.longitude}&radius_miles=${radius}`
      );
      
      if (!response.ok) throw new Error('Failed to get nearby events');
      
      const data = await response.json();
      return data.success ? data.events : [];
    } catch (err) {
      console.error('Error getting nearby events:', err);
      return [];
    }
  }, [userLocation, preferredRadius]);
  
  /**
   * Select a city manually
   */
  const selectCity = useCallback((cityCode: string) => {
    setSelectedCity(cityCode);
    onLocationChange?.(cityCode);
    
    // Save preference
    savePreference({
      major_city_code: cityCode,
      auto_detect: false
    });
  }, [onLocationChange]);
  
  /**
   * Save location preference
   */
  const savePreference = useCallback(async (preference: Partial<LocationPreference>) => {
    try {
      const existing = loadPreference();
      const updated: LocationPreference = {
        ...existing,
        ...preference,
        stored_at: new Date().toISOString()
      };
      
      localStorage.setItem(LOCATION_PREF_KEY, JSON.stringify(updated));
      
      // Also save to server if user_id available
      const userId = localStorage.getItem('user_id');
      if (userId) {
        await fetch(`${API_BASE_URL}/api/locations/preferences`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            major_city_code: updated.major_city_code,
            latitude: updated.secondary_location?.latitude,
            longitude: updated.secondary_location?.longitude,
            auto_detect: updated.auto_detect,
            preferred_radius: updated.preferred_radius
          })
        });
      }
    } catch (err) {
      console.error('Error saving preference:', err);
    }
  }, []);
  
  /**
   * Load location preference
   */
  const loadPreference = useCallback((): LocationPreference | null => {
    try {
      const stored = localStorage.getItem(LOCATION_PREF_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }, []);
  
  /**
   * Check if city is nearby
   */
  const isNearby = useCallback((cityCode: string, maxDistance: number = preferredRadius): boolean => {
    if (!userLocation) return false;
    
    const city = nearbyCities.find(c => c.code === cityCode);
    if (!city || city.distance_miles === undefined) return false;
    
    return city.distance_miles <= maxDistance;
  }, [userLocation, nearbyCities, preferredRadius]);
  
  /**
   * Cache location in localStorage
   */
  const cacheLocation = (coords: Coordinates) => {
    try {
      const cache = {
        coords,
        timestamp: Date.now()
      };
      localStorage.setItem(LOCATION_CACHE_KEY, JSON.stringify(cache));
    } catch (e) {
      console.warn('Failed to cache location:', e);
    }
  };
  
  /**
   * Get cached location if still valid
   */
  const getCachedLocation = (): Coordinates | null => {
    try {
      const cached = localStorage.getItem(LOCATION_CACHE_KEY);
      if (!cached) return null;
      
      const { coords, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp > CACHE_DURATION) {
        localStorage.removeItem(LOCATION_CACHE_KEY);
        return null;
      }
      
      return coords;
    } catch {
      return null;
    }
  };
  
  /**
   * Auto-detect on mount if enabled
   */
  useEffect(() => {
    if (autoDetect) {
      // Check for saved preference first
      const saved = loadPreference();
      if (saved) {
        setSelectedCity(saved.major_city_code);
        onLocationChange?.(saved.major_city_code);
        
        if (saved.auto_detect) {
          detectLocation();
        }
      } else {
        detectLocation();
      }
    }
  }, []);
  
  return {
    // State
    userLocation,
    nearestCity,
    nearbyCities,
    selectedCity,
    isDetecting,
    error,
    
    // Actions
    detectLocation,
    selectCity,
    findNearestCity,
    getNearbyCities,
    getEventsNearby,
    savePreference,
    loadPreference,
    
    // Utilities
    calculateDistance,
    isNearby
  };
}

export default useGeolocation;
