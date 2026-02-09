/**
 * Geolocation Detection and Management
 * 
 * Handles:
 * - Browser geolocation detection
 * - Coordinates storage in localStorage/cookies
 * - Nearest city detection
 * - User preference persistence
 */

interface Coordinates {
  latitude: number;
  longitude: number;
}

interface LocationPreference {
  majorCity: string;
  secondaryLocation?: Coordinates;
  autoDetect: boolean;
  preferredRadius: number;
  storedAt: string;
}

const LOCATION_STORAGE_KEY = 'inyacity_location_preference';
const GEOLOCATION_CACHE_KEY = 'inyacity_user_location';
const GEOLOCATION_CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Request browser geolocation permission
 * Returns coordinates or null if denied
 */
export async function requestBrowserLocation(): Promise<Coordinates | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      console.warn('Geolocation not supported by browser');
      resolve(null);
      return;
    }

    const options = {
      enableHighAccuracy: false, // Standard accuracy is fine
      timeout: 10000,            // 10 second timeout
      maximumAge: 60000          // Cache for 1 minute
    };

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coords: Coordinates = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        };
        resolve(coords);
      },
      (error) => {
        console.warn(`Geolocation error: ${error.message}`);
        resolve(null);
      },
      options
    );
  });
}

/**
 * Get cached user location or request new one
 */
export async function getUserLocation(): Promise<Coordinates | null> {
  // Check cache first
  const cached = getCachedLocation();
  if (cached) {
    return cached;
  }

  // Request new location
  const location = await requestBrowserLocation();
  
  if (location) {
    cacheLocation(location);
  }

  return location;
}

/**
 * Store location in cache
 */
function cacheLocation(coords: Coordinates): void {
  const cache = {
    coords,
    timestamp: Date.now()
  };
  
  try {
    localStorage.setItem(GEOLOCATION_CACHE_KEY, JSON.stringify(cache));
  } catch (e) {
    console.warn('Failed to cache location:', e);
  }
}

/**
 * Get cached location if still valid
 */
function getCachedLocation(): Coordinates | null {
  try {
    const cached = localStorage.getItem(GEOLOCATION_CACHE_KEY);
    if (!cached) return null;

    const { coords, timestamp } = JSON.parse(cached);
    
    // Check if cache is still valid
    if (Date.now() - timestamp > GEOLOCATION_CACHE_DURATION) {
      localStorage.removeItem(GEOLOCATION_CACHE_KEY);
      return null;
    }

    return coords;
  } catch (e) {
    console.warn('Failed to retrieve cached location:', e);
    return null;
  }
}

/**
 * Save user's location preference (major city + optional fine-grained)
 */
export function saveLocationPreference(
  majorCity: string,
  secondary?: Coordinates,
  autoDetect: boolean = true,
  preferredRadius: number = 25
): void {
  const preference: LocationPreference = {
    majorCity,
    secondaryLocation: secondary,
    autoDetect,
    preferredRadius,
    storedAt: new Date().toISOString()
  };

  try {
    localStorage.setItem(LOCATION_STORAGE_KEY, JSON.stringify(preference));
  } catch (e) {
    console.warn('Failed to save location preference:', e);
  }
}

/**
 * Get saved location preference
 */
export function getLocationPreference(): LocationPreference | null {
  try {
    const stored = localStorage.getItem(LOCATION_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch (e) {
    console.warn('Failed to retrieve location preference:', e);
    return null;
  }
}

/**
 * Clear location data from storage
 */
export function clearLocationData(): void {
  try {
    localStorage.removeItem(LOCATION_STORAGE_KEY);
    localStorage.removeItem(GEOLOCATION_CACHE_KEY);
  } catch (e) {
    console.warn('Failed to clear location data:', e);
  }
}

/**
 * Find nearest major city from coordinates
 */
export async function findNearestCity(
  coords: Coordinates,
  apiBaseUrl: string = '/api'
): Promise<any | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/locations/nearest-cities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitude: coords.latitude,
        longitude: coords.longitude,
        limit: 1
      })
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);

    const data = await response.json();
    return data.success && data.results.length > 0 ? data.results[0] : null;
  } catch (error) {
    console.error('Failed to find nearest city:', error);
    return null;
  }
}

/**
 * Get nearby locations within radius
 */
export async function getNearbyLocations(
  coords: Coordinates,
  radiusMiles: number = 25,
  apiBaseUrl: string = '/api'
): Promise<any[]> {
  try {
    const response = await fetch(`${apiBaseUrl}/locations/nearby`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitude: coords.latitude,
        longitude: coords.longitude,
        radius_miles: radiusMiles,
        tier: 'major'
      })
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);

    const data = await response.json();
    return data.success ? data.results : [];
  } catch (error) {
    console.error('Failed to get nearby locations:', error);
    return [];
  }
}

/**
 * Complete geolocation workflow:
 * 1. Check for saved preference
 * 2. Request browser location if auto-detect enabled
 * 3. Find nearest city
 * 4. Save preference
 */
export async function initializeLocationDetection(
  apiBaseUrl: string = '/api'
): Promise<string | null> {
  // Check for existing preference
  const saved = getLocationPreference();
  if (saved && saved.majorCity && !saved.autoDetect) {
    return saved.majorCity;
  }

  // Get user's location
  const userLocation = await getUserLocation();
  if (!userLocation) {
    console.warn('Could not determine user location');
    return saved?.majorCity || null;
  }

  // Find nearest city
  const nearest = await findNearestCity(userLocation, apiBaseUrl);
  if (!nearest) {
    return saved?.majorCity || null;
  }

  // Save preference
  const cityCode = nearest.location.code;
  saveLocationPreference(
    cityCode,
    userLocation,
    true,
    25
  );

  return cityCode;
}

/**
 * Check if geolocation is available in browser
 */
export function isGeolocationSupported(): boolean {
  return !!navigator.geolocation;
}

/**
 * Request user permission for geolocation with UI feedback
 */
export async function requestLocationWithFallback(
  options?: {
    showPrompt?: boolean;
    promptMessage?: string;
    onPrompt?: (accepted: boolean) => void;
  }
): Promise<Coordinates | null> {
  const { showPrompt = true, promptMessage = 'Allow location access for better recommendations?', onPrompt } = options || {};

  if (!isGeolocationSupported()) {
    return null;
  }

  // Show custom prompt if desired
  if (showPrompt) {
    const userAccepted = window.confirm(promptMessage);
    onPrompt?.(userAccepted);
    
    if (!userAccepted) {
      return null;
    }
  }

  return await getUserLocation();
}
