import React, { useState, useEffect, useRef, useCallback } from 'react';
import { City } from '../types';
import { ArrowRight, Loader2, MapPin, Search, X } from 'lucide-react';
import { searchCities } from '../services/apiService';
import { useGeolocation } from '../src/hooks/useGeolocation';

interface SearchResult {
  code: string;
  name: string;
  tier: string;
  state: string;
  country: string;
  coordinates: { latitude: number; longitude: number };
  population?: number;
  scraped: boolean;
}

interface CitySelectorProps {
  onSelect: (city: City) => void;
  cities: City[];
  initialLoad?: boolean;
}

const CitySelector: React.FC<CitySelectorProps> = ({ onSelect, cities, initialLoad = false }) => {
  const [hoveredCity, setHoveredCity] = useState<string | null>(null);
  const [focusedCityIndex, setFocusedCityIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const searchDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const typedSearch = useRef('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [searchDisplay, setSearchDisplay] = useState('');

  const {
    nearestCity,
    selectedCity: detectedCityCode,
    isDetecting,
    error: detectError,
    detectLocation,
    selectCity: saveCityPreference,
    loadPreference,
  } = useGeolocation({ autoDetect: false });

  const ipFallbackRef = useRef(false);
  const detectionStartedRef = useRef(false);

  // Persist preference when user picks a city
  const handleSelect = useCallback((city: City) => {
    saveCityPreference(city.id);
    onSelect(city);
  }, [onSelect, saveCityPreference]);

  // Auto-detect on mount (saved preference → old cache → browser geo → IP fallback)
  useEffect(() => {
    if (cities.length === 0 || detectionStartedRef.current) return;
    detectionStartedRef.current = true;

    // 1. Saved preference from hook's system
    const saved = loadPreference();
    if (saved?.major_city_code && !saved.auto_detect) {
      const match = cities.find(c => c.id === saved.major_city_code);
      if (match) { onSelect(match); return; }
    }

    // 2. Old cache migration
    const oldCached = localStorage.getItem('nocturne_nearest_city');
    if (oldCached) {
      localStorage.removeItem('nocturne_nearest_city');
      const match = cities.find(c => c.id === oldCached);
      if (match) {
        saveCityPreference(match.id);
        onSelect(match);
        return;
      }
    }

    // 3. Browser geo + nearest-cities API
    detectLocation();
  }, [cities.length]);

  // IP geo fallback when browser geo fails
  useEffect(() => {
    if (detectError && !nearestCity && !ipFallbackRef.current) {
      ipFallbackRef.current = true;
      (async () => {
        try {
          const ipResp = await fetch('/api/locations/detect');
          if (ipResp.ok) {
            const data = await ipResp.json();
            const nearest = data.nearest_cities?.[0]?.location;
            if (nearest?.code) {
              saveCityPreference(nearest.code);
            }
          }
        } catch {
          // silent
        }
      })();
    }
  }, [detectError, nearestCity, saveCityPreference]);

  // Auto-select when nearest city detected or preference loaded
  const prevDetectedRef = useRef<string | null>(null);
  useEffect(() => {
    const code = detectedCityCode ?? nearestCity?.code ?? null;
    if (code && code !== prevDetectedRef.current) {
      prevDetectedRef.current = code;
      const match = cities.find(c => c.id === code);
      if (match) onSelect(match);
    }
  }, [nearestCity, detectedCityCode, cities, onSelect]);

  // Search API — debounced, calls /api/locations/search
  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    if (!searchQuery.trim() || searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    searchDebounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const result = await searchCities(searchQuery.trim());
        setSearchResults(result.results || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, [searchQuery]);

  const handleSearchSelect = async (r: SearchResult) => {
    setSearchQuery('');
    setSearchResults([]);
    saveCityPreference(r.code);
    const match = cities.find(c => c.id === r.code);
    if (match) { onSelect(match); return; }
    // City exists in DB but not in local list — still selectable
    const pseudoCity: City = {
      id: r.code,
      name: r.name.toUpperCase(),
      slug: r.code,
      coordinates: { lat: r.coordinates.latitude, lng: r.coordinates.longitude },
    };
    onSelect(pseudoCity);
  };

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setSearchDisplay('');
        typedSearch.current = '';
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
          searchTimeoutRef.current = null;
        }
        return;
      }

      if (e.key === 'Backspace') {
        e.preventDefault();
        typedSearch.current = typedSearch.current.slice(0, -1);
        setSearchDisplay(typedSearch.current);
        const q = typedSearch.current.toLowerCase();
        if (q) {
          const idx = cities.findIndex(c => c.name.toLowerCase().startsWith(q));
          if (idx >= 0) {
            setFocusedCityIndex(idx);
            setHoveredCity(cities[idx].id);
          }
        }
        if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
        if (typedSearch.current) {
          searchTimeoutRef.current = setTimeout(() => {
            typedSearch.current = '';
            setSearchDisplay('');
          }, 1500);
        }
        return;
      }

      if (e.key.length === 1 && e.key.match(/[a-zA-Z]/) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        typedSearch.current = (typedSearch.current + e.key.toLowerCase()).slice(0, 3);
        setSearchDisplay(typedSearch.current);
        const idx = cities.findIndex(c => c.name.toLowerCase().startsWith(typedSearch.current));
        if (idx >= 0) {
          setFocusedCityIndex(idx);
          setHoveredCity(cities[idx].id);
        }
        if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
        searchTimeoutRef.current = setTimeout(() => {
          typedSearch.current = '';
          setSearchDisplay('');
        }, 1500);
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setFocusedCityIndex(p => (p + 1) % cities.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setFocusedCityIndex(p => (p - 1 + cities.length) % cities.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (buttonRefs.current[focusedCityIndex]) {
          handleSelect(cities[focusedCityIndex]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, [cities, focusedCityIndex, handleSelect]);

  useEffect(() => {
    if (buttonRefs.current[focusedCityIndex]) {
      buttonRefs.current[focusedCityIndex]?.focus();
      setHoveredCity(cities[focusedCityIndex]?.id || null);
      buttonRefs.current[focusedCityIndex]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [focusedCityIndex, cities]);

  if (initialLoad) {
    return (
      <div className="h-screen w-full flex flex-col justify-center items-center px-4 md:px-12 lg:px-24 bg-void text-concrete overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="z-10 flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-acid w-12 h-12" />
          <p className="font-mono text-zinc-500 text-sm animate-pulse">INITIALIZING NOCTURNE NETWORK...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex flex-col px-4 md:px-12 lg:px-24 bg-void text-concrete py-20 relative">
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] z-0"></div>

      {/* Type-ahead indicator */}
      {searchDisplay && (
        <div className="fixed top-24 right-12 z-50 font-mono text-2xl font-bold text-acid bg-void/80 px-4 py-2 border border-acid/30">
          {searchDisplay.toUpperCase()}
        </div>
      )}

      {/* Auto-detect status bar */}
      <div className="z-10 flex items-center gap-4 mb-4 ml-1">
        <h1 className="text-sm font-mono tracking-widest text-zinc-500 uppercase">Select Sector</h1>
        {isDetecting ? (
          <span className="flex items-center gap-2 font-mono text-xs text-zinc-500">
            <Loader2 className="animate-spin w-3 h-3" />
            DETECTING LOCATION...
          </span>
        ) : detectError ? (
          <button onClick={detectLocation} className="flex items-center gap-1 font-mono text-xs text-zinc-600 hover:text-acid transition-colors">
            <MapPin className="w-3 h-3" />
            LOCATION FAILED — RETRY
          </button>
        ) : nearestCity ? (
          <span className="flex items-center gap-1 font-mono text-xs text-acid/60">
            <MapPin className="w-3 h-3" />
            {nearestCity.name}
          </span>
        ) : (
          <button onClick={detectLocation} className="flex items-center gap-1 font-mono text-xs text-zinc-600 hover:text-acid transition-colors">
            <MapPin className="w-3 h-3" />
            DETECT MY LOCATION
          </button>
        )}
      </div>

      {/* Search bar */}
      <div className="z-10 relative mb-8">
        <div className="flex items-center border border-zinc-700 focus-within:border-acid transition-colors bg-void">
          <Search className="ml-3 w-4 h-4 text-zinc-500 flex-shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search cities... (e.g. Miami, Austin, Tokyo)"
            className="w-full bg-transparent px-3 py-3 font-mono text-sm text-white placeholder-zinc-600 focus:outline-none"
          />
          {searchQuery && (
            <button onClick={() => { setSearchQuery(''); setSearchResults([]); }} className="mr-2 p-1 text-zinc-500 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          )}
          {searching && <Loader2 className="mr-3 w-4 h-4 text-zinc-500 animate-spin flex-shrink-0" />}
        </div>

        {/* Search results dropdown */}
        {searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 border border-zinc-700 bg-void max-h-60 overflow-y-auto">
            {searchResults.map(r => (
              <button
                key={r.code}
                onClick={() => handleSearchSelect(r)}
                className="w-full text-left px-4 py-3 border-b border-zinc-800 hover:bg-zinc-900 transition-colors flex items-center justify-between"
              >
                <div>
                  <span className="font-mono text-sm text-white">{r.name}</span>
                  <span className="font-mono text-xs text-zinc-600 ml-2">{r.state}, {r.country}</span>
                </div>
                <span className="font-mono text-xs text-acid">SELECT</span>
              </button>
            ))}
          </div>
        )}

        {searchQuery && searchQuery.trim().length >= 2 && !searching && searchResults.length === 0 && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 border border-zinc-700 bg-void p-4">
            <p className="font-mono text-xs text-zinc-500">CITY NOT RECOGNIZED</p>
          </div>
        )}
      </div>

      <div className="z-10 flex flex-col gap-0">
        {cities.map((city, index) => (
          <button
            key={city.id}
            ref={(el) => { buttonRefs.current[index] = el; }}
            onMouseEnter={() => {
              setHoveredCity(city.id);
              setFocusedCityIndex(index);
            }}
            onMouseLeave={() => setHoveredCity(null)}
            onClick={() => handleSelect(city)}
            className="group relative flex items-center justify-between w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-acid focus-visible:ring-offset-2 focus-visible:ring-offset-void py-2 px-1 border-b border-concrete hover:border-acid transition-colors duration-500"
          >
            <div className="flex items-center gap-4">
              {nearestCity?.code === city.id && (
                <MapPin className="text-acid w-5 h-5 flex-shrink-0" />
              )}
              <span
                className={`
                  text-5xl md:text-8xl lg:text-9xl font-black tracking-tighter transition-all duration-500 ease-out leading-none
                  ${hoveredCity === city.id ? 'text-acid translate-x-4 skew-x-12' : 'text-zinc-600 group-hover:text-zinc-400'}
                  ${nearestCity?.code === city.id ? 'text-acid/40' : ''}
                `}
              >
                {city.name}
              </span>
            </div>

            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center gap-4 flex-shrink-0">
              <span className="font-mono text-xs text-acid hidden md:block whitespace-nowrap">
                [{city.coordinates.lat.toFixed(2)}, {city.coordinates.lng.toFixed(2)}]
              </span>
              <ArrowRight className="text-acid w-8 h-8 md:w-16 md:h-16 -rotate-45 group-hover:rotate-0 transition-transform duration-500 flex-shrink-0" />
            </div>

            {hoveredCity === city.id && (
              <div className="fixed top-0 right-0 w-1/3 h-full object-cover opacity-20 pointer-events-none mix-blend-screen z-[-1] hidden lg:block transition-opacity duration-700">
                <img src={`https://picsum.photos/800/1200?random=${city.id}`} alt="city vibe" className="w-full h-full object-cover grayscale brightness-50" />
              </div>
            )}
          </button>
        ))}
      </div>

      <div className="fixed bottom-12 left-12 font-mono text-xs text-zinc-600 z-10">
        NOCTURNE SYSTEM v2.0
      </div>
    </div>
  );
};

export default CitySelector;
