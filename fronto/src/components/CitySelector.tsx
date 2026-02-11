/**
 * City Selector Component
 * 
 * Features:
 * - Display major cities in scrollable list
 * - Auto-detect and highlight nearest city
 * - Store user preference
 * - Support for secondary/fine-grained location filtering
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  initializeLocationDetection, 
  getLocationPreference,
  saveLocationPreference,
  getNearbyLocations,
  isGeolocationSupported,
  requestLocationWithFallback 
} from '../utils/geolocation';

interface City {
  id: string;
  code: string;
  name: string;
  tier: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  state: string;
  country: string;
  population?: number;
  timezone?: string;
}

interface CityListProps {
  onCitySelect: (cityCode: string) => void;
  apiBaseUrl?: string;
  showAutoDetect?: boolean;
  showSecondaryLocations?: boolean;
  maxDisplayCities?: number;
}

export const CitySelector: React.FC<CityListProps> = ({
  onCitySelect,
  apiBaseUrl = '/api',
  showAutoDetect = true,
  showSecondaryLocations = true,
  maxDisplayCities = 50
}) => {
  const [cities, setCities] = useState<City[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [nearestCity, setNearestCity] = useState<string | null>(null);
  const [nearbyLocations, setNearbyLocations] = useState<City[]>([]);
  const [autoDetectEnabled, setAutoDetectEnabled] = useState(true);
  const [typedSearch, setTypedSearch] = useState('');
  const [filteredCities, setFilteredCities] = useState<City[]>([]);
  const selectedCityRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load major cities on mount
  useEffect(() => {
    loadMajorCities();
  }, []);

  // Auto-detect location and scroll to nearest city
  useEffect(() => {
    if (showAutoDetect && autoDetectEnabled) {
      performAutoDetection();
    }
  }, [showAutoDetect, autoDetectEnabled]);

  // Scroll to selected city when it changes
  useEffect(() => {
    if (selectedCityRef.current && containerRef.current) {
      scrollToCity();
    }
  }, [selectedCity]);

  // Type-ahead search functionality
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input field
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Handle letters only
      if (e.key.length === 1 && e.key.match(/[a-zA-Z]/)) {
        // Skip if modifier keys are active (Ctrl, Meta, Alt) to avoid blocking browser shortcuts
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        
        e.preventDefault();

        const newSearch = typedSearch + e.key.toLowerCase();
        setTypedSearch(newSearch);

        // Filter cities based on search
        const matching = cities.filter(city =>
          city.name.toLowerCase().startsWith(newSearch) ||
          city.state.toLowerCase().startsWith(newSearch)
        );

        if (matching.length > 0) {
          setFilteredCities(matching);
          // Scroll to first match
          const firstMatch = matching[0];
          setSelectedCity(firstMatch.code);
        } else {
          // Clear the filtered list when no matches are found
          setFilteredCities([]);
        }

        // Clear search after 1.5 seconds of inactivity
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
        searchTimeoutRef.current = setTimeout(() => {
          setTypedSearch('');
          setFilteredCities([]);
        }, 1500);
      }

      // Escape clears search
      if (e.key === 'Escape') {
        setTypedSearch('');
        setFilteredCities([]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [cities, typedSearch]);

  /**
   * Fetch major cities from API
   */
  async function loadMajorCities(): Promise<void> {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/locations/major-cities?limit=${maxDisplayCities}&sort_by=name`);
      
      if (!response.ok) throw new Error('Failed to load cities');
      
      const data = await response.json();
      if (data.success) {
        setCities(data.cities);
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Failed to load cities:', err);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Auto-detect user location and find nearest city
   */
  async function performAutoDetection(): Promise<void> {
    try {
      // Check for saved preference first
      const saved = getLocationPreference();
      if (saved?.majorCity) {
        setSelectedCity(saved.majorCity);
        setNearestCity(saved.majorCity);
        return;
      }

      // Request location
      const location = await requestLocationWithFallback({
        showPrompt: true,
        promptMessage: 'Enable location services for personalized city recommendations?'
      });

      if (location) {
        // Find nearest city
        const response = await fetch(`${apiBaseUrl}/locations/nearest-cities`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            latitude: location.latitude,
            longitude: location.longitude,
            limit: 1
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.results.length > 0) {
            const nearest = data.results[0].location.code;
            setSelectedCity(nearest);
            setNearestCity(nearest);
            
            // Save preference
            saveLocationPreference(
              nearest,
              location,
              true,
              25
            );

            // Load nearby locations if enabled
            if (showSecondaryLocations) {
              loadNearbyLocations(location);
            }
          }
        }
      } else {
        setAutoDetectEnabled(false);
      }
    } catch (err) {
      console.error('Auto-detection failed:', err);
      setAutoDetectEnabled(false);
    }
  }

  /**
   * Load nearby/secondary locations
   */
  async function loadNearbyLocations(coords: { latitude: number; longitude: number }): Promise<void> {
    try {
      const response = await fetch(`${apiBaseUrl}/locations/nearby`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: coords.latitude,
          longitude: coords.longitude,
          radius_miles: 50
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setNearbyLocations(data.results.map((r: any) => r.location));
        }
      }
    } catch (err) {
      console.error('Failed to load nearby locations:', err);
    }
  }

  /**
   * Scroll selected city into view
   */
  function scrollToCity(): void {
    if (!selectedCityRef.current || !containerRef.current) return;

    const element = selectedCityRef.current;
    const container = containerRef.current;

    const elementTop = element.offsetTop;
    const elementHeight = element.offsetHeight;
    const containerTop = container.scrollTop;
    const containerHeight = container.offsetHeight;

    // Calculate scroll position to center the element
    let scrollTop = elementTop - (containerHeight - elementHeight) / 2;
    scrollTop = Math.max(0, Math.min(scrollTop, container.scrollHeight - containerHeight));

    // Slower, smoother scroll with custom duration
    const startTop = container.scrollTop;
    const distance = scrollTop - startTop;
    const duration = 800; // Slightly slower (800ms instead of default ~300ms)
    const startTime = performance.now();

    const animateScroll = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Ease out cubic for smoother feel
      const easeOut = 1 - Math.pow(1 - progress, 3);
      
      container.scrollTop = startTop + (distance * easeOut);
      
      if (progress < 1) {
        requestAnimationFrame(animateScroll);
      }
    };

    requestAnimationFrame(animateScroll);
  }

  /**
   * Sanitize string to prevent XSS
   */
  function sanitizeString(str: string): string {
    if (!str) return '';
    // Replace HTML entities to prevent XSS
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;');
  }

  /**
   * Highlight matching letters in city name
   */
  function HighlightMatch({ name, search }: { name: string; search: string }) {
    if (!search) return <>{sanitizeString(name)}</>;
    const lowerName = name.toLowerCase();
    const lowerSearch = search.toLowerCase();
    if (lowerName.startsWith(lowerSearch)) {
      const matched = name.substring(0, search.length);
      const rest = name.substring(search.length);
      return (
        <>
          <span className="highlight">{sanitizeString(matched)}</span>
          {sanitizeString(rest)}
        </>
      );
    }
    return <>{sanitizeString(name)}</>;
  }

  /**
   * Handle city selection
   */
  function handleCitySelect(cityCode: string): void {
    setSelectedCity(cityCode);
    saveLocationPreference(cityCode, undefined, false, 25);
    onCitySelect(cityCode);
  }

  if (loading) {
    return (
      <div className="city-selector loading">
        <div className="spinner">Loading cities...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="city-selector error">
        <p>Error loading cities: {error}</p>
        <button onClick={() => loadMajorCities()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="city-selector-container">
      {/* Auto-detect indicator */}
      {showAutoDetect && (
        <div className="auto-detect-info">
          {isGeolocationSupported() ? (
            <>
              <span className="badge-geolocation">
                📍 Location services {autoDetectEnabled ? 'enabled' : 'disabled'}
              </span>
              {nearestCity && (
                <span className="badge-nearest">
                  📍 Nearest city detected: {cities.find(c => c.code === nearestCity)?.name}
                </span>
              )}
            </>
          ) : (
            <span className="badge-no-geolocation">
              📍 Geolocation not supported
            </span>
          )}
        </div>
      )}

      {/* Major cities list */}
      <div className="city-list-section">
        <div className="city-list-header">
          <h3>Major Cities</h3>
          {typedSearch ? (
            <div className="search-indicator">
              <span className="search-letters">{typedSearch}</span>
              <span className="search-hint">({filteredCities.length} found)</span>
            </div>
          ) : (
            <span className="type-hint">Type to search...</span>
          )}
        </div>
        <div className="city-list-container" ref={containerRef}>
          {(filteredCities.length > 0 ? filteredCities : cities).map((city) => {
            // Highlight matching letters if searching
            const cityName = city.name;

            return (
            <div
              key={city.code}
              ref={city.code === selectedCity ? selectedCityRef : undefined}
              className={`city-item ${
                city.code === selectedCity ? 'selected' : ''
              } ${city.code === nearestCity ? 'nearest' : ''} ${
                filteredCities.find(c => c.code === city.code) ? 'search-match' : ''
              }`}
              onClick={() => handleCitySelect(city.code)}
              role="button"
              tabIndex={0}
              onKeyPress={(e) => {
                if (e.key === 'Enter') handleCitySelect(city.code);
              }}
            >
              <div className="city-name">
                <HighlightMatch name={cityName} search={typedSearch} />
              </div>
              <div className="city-meta">
                {city.population && (
                  <span className="population">
                    {(city.population / 1000000).toFixed(1)}M
                  </span>
                )}
                <span className="state">{city.state}</span>
              </div>
              {city.code === nearestCity && (
                <div className="badge-nearest-indicator">📍 Nearest</div>
              )}
              {city.code === selectedCity && (
                <div className="badge-selected-indicator">✓ Selected</div>
              )}
            </div>
            );
          })}
        </div>
      </div>

      {/* Secondary/nearby locations (if enabled and available) */}
      {showSecondaryLocations && nearbyLocations.length > 0 && (
        <div className="nearby-locations-section">
          <h3>Nearby Secondary Locations</h3>
          <div className="nearby-locations-grid">
            {nearbyLocations.slice(0, 12).map((location) => (
              <div
                key={location.code}
                className="nearby-location-item"
                onClick={() => handleCitySelect(location.code)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') handleCitySelect(location.code);
                }}
              >
                <div className="location-name">{location.name}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CSS Styles */}
      <style>{`
        .city-selector-container {
          padding: 20px;
          max-width: 600px;
          margin: 0 auto;
        }

        .auto-detect-info {
          margin-bottom: 20px;
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          font-size: 14px;
        }

        .badge-geolocation,
        .badge-nearest,
        .badge-no-geolocation {
          padding: 8px 12px;
          border-radius: 4px;
          background: #f0f0f0;
          border-left: 3px solid #2196F3;
        }

        .city-list-section {
          margin-bottom: 30px;
        }

        .city-list-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
        }

        .city-list-section h3 {
          margin: 0;
          font-size: 18px;
          color: #333;
        }

        .search-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
        }

        .search-letters {
          background: #2196F3;
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-weight: bold;
          font-family: monospace;
          letter-spacing: 2px;
        }

        .search-hint {
          color: #666;
          font-size: 12px;
        }

        .type-hint {
          color: #999;
          font-size: 12px;
          font-style: italic;
        }

        .city-list-container {
          border: 1px solid #ddd;
          border-radius: 8px;
          max-height: 400px;
          overflow-y: auto;
          background: white;
          scroll-behavior: smooth;
          /* Slower, smoother scrolling for mouse wheel */
          scroll-padding: 20px;
        }

        /* Webkit scrollbar styling for smoother appearance */
        .city-list-container::-webkit-scrollbar {
          width: 8px;
        }

        .city-list-container::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 4px;
        }

        .city-list-container::-webkit-scrollbar-thumb {
          background: #c1c1c1;
          border-radius: 4px;
        }

        .city-list-container::-webkit-scrollbar-thumb:hover {
          background: #a8a8a8;
        }

        .city-item {
          padding: 12px 15px;
          border-bottom: 1px solid #eee;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: relative;
        }

        .city-item:last-child {
          border-bottom: none;
        }

        .city-item:hover {
          background-color: #f9f9f9;
        }

        .city-item.selected {
          background-color: #e3f2fd;
          border-left: 4px solid #2196F3;
          padding-left: 12px;
        }

        .city-item.nearest {
          border-left: 4px solid #ff9800;
        }

        .city-item.search-match {
          background-color: #fff8e1;
        }

        .city-item.search-match:hover {
          background-color: #ffecb3;
        }

        .city-name .highlight {
          background-color: #2196F3;
          color: white;
          padding: 0 2px;
          border-radius: 2px;
        }

        .city-name {
          font-weight: 500;
          color: #333;
        }

        .city-meta {
          display: flex;
          gap: 10px;
          font-size: 12px;
          color: #666;
        }

        .population {
          background: #f0f0f0;
          padding: 2px 6px;
          border-radius: 3px;
        }

        .state {
          color: #999;
        }

        .badge-nearest-indicator,
        .badge-selected-indicator {
          font-size: 12px;
          padding: 4px 8px;
          border-radius: 3px;
          background: #e3f2fd;
          color: #2196F3;
          margin-left: 10px;
        }

        .nearby-locations-section {
          margin-top: 30px;
        }

        .nearby-locations-section h3 {
          margin: 0 0 15px 0;
          font-size: 18px;
          color: #333;
        }

        .nearby-locations-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          gap: 10px;
        }

        .nearby-location-item {
          padding: 15px;
          border: 1px solid #ddd;
          border-radius: 6px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
        }

        .nearby-location-item:hover {
          border-color: #2196F3;
          background-color: #f9f9f9;
        }

        .location-name {
          font-size: 14px;
          color: #333;
          font-weight: 500;
        }

        .city-selector.loading,
        .city-selector.error {
          padding: 40px 20px;
          text-align: center;
        }

        .spinner {
          font-size: 16px;
          color: #666;
        }

        .city-selector.error {
          background: #ffebee;
          border: 1px solid #ef5350;
          border-radius: 4px;
          color: #c62828;
        }

        .city-selector.error button {
          margin-top: 10px;
          padding: 8px 16px;
          background: #2196F3;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .city-selector.error button:hover {
          background: #1976D2;
        }
      `}</style>
    </div>
  );
};

export default CitySelector;
