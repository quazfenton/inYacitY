import React, { useState, useEffect, useRef } from 'react';
import { City } from '../types';
import { ArrowRight, Loader2 } from 'lucide-react';

interface CitySelectorProps {
  onSelect: (city: City) => void;
  cities: City[];
  initialLoad?: boolean;
}

const CitySelector: React.FC<CitySelectorProps> = ({ onSelect, cities, initialLoad = false }) => {
  const [hoveredCity, setHoveredCity] = useState<string | null>(null);
  const [focusedCityIndex, setFocusedCityIndex] = useState(0);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  
  // Type-ahead search state
  const [typedSearch, setTypedSearch] = useState('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Handle Escape key - clear search
      if (e.key === 'Escape') {
        e.preventDefault();
        setTypedSearch('');
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
          searchTimeoutRef.current = null;
        }
        return;
      }

      // Handle Backspace key - remove last character
      if (e.key === 'Backspace') {
        e.preventDefault();
        setTypedSearch(prev => {
          const newSearch = prev.slice(0, -1);
          // Update focus based on new search
          if (newSearch.length > 0) {
            const matchingIndex = cities.findIndex(city => 
              city.name.toLowerCase().startsWith(newSearch.toLowerCase())
            );
            if (matchingIndex >= 0) {
              setFocusedCityIndex(matchingIndex);
              setHoveredCity(cities[matchingIndex].id);
            }
          }
          return newSearch;
        });
        // Reset the clear timeout
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
        if (typedSearch.length > 1) {
          searchTimeoutRef.current = setTimeout(() => {
            setTypedSearch('');
          }, 1500);
        }
        return;
      }

      // Handle type-ahead search (letters only, not when modifier keys pressed)
      if (e.key.length === 1 && e.key.match(/[a-zA-Z]/) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        
        const newSearch = (typedSearch + e.key.toLowerCase()).slice(0, 3); // max 3 chars
        setTypedSearch(newSearch);
        
        // Find first matching city
        const matchingIndex = cities.findIndex(city => 
          city.name.toLowerCase().startsWith(newSearch)
        );
        
        if (matchingIndex >= 0) {
          setFocusedCityIndex(matchingIndex);
          setHoveredCity(cities[matchingIndex].id);
        }
        
        // Clear search after 1.5 seconds of inactivity
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
        searchTimeoutRef.current = setTimeout(() => {
          setTypedSearch('');
        }, 1500);
        
        return;
      }
      
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setFocusedCityIndex(prev => (prev + 1) % cities.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setFocusedCityIndex(prev => (prev - 1 + cities.length) % cities.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (buttonRefs.current[focusedCityIndex]) {
          onSelect(cities[focusedCityIndex]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [cities, focusedCityIndex, onSelect, typedSearch]);

  // Auto-focus and scroll to focused city
  useEffect(() => {
    if (buttonRefs.current[focusedCityIndex]) {
      buttonRefs.current[focusedCityIndex]?.focus();
      setHoveredCity(cities[focusedCityIndex]?.id || null);
      // Scroll into view
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
      {/* Background Noise/Grid Effect */}
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] z-0"></div>

      {/* Type-ahead indicator */}
      {typedSearch && (
        <div className="fixed top-24 right-12 z-50 font-mono text-2xl font-bold text-acid bg-void/80 px-4 py-2 border border-acid/30">
          {typedSearch.toUpperCase()}
        </div>
      )}

      <div className="z-10 flex flex-col gap-0">
        <h1 className="text-sm font-mono tracking-widest text-zinc-500 mb-8 ml-1 uppercase">Select Sector</h1>
        
        {cities.map((city, index) => (
          <button
            key={city.id}
            ref={(el) => { buttonRefs.current[index] = el; }}
            onMouseEnter={() => {
              setHoveredCity(city.id);
              setFocusedCityIndex(index);
            }}
            onMouseLeave={() => setHoveredCity(null)}
            onClick={() => onSelect(city)}
            className="group relative flex items-center justify-between w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-acid focus-visible:ring-offset-2 focus-visible:ring-offset-void py-2 px-1 border-b border-concrete hover:border-acid transition-colors duration-500"
          >
            <span 
              className={`
                text-5xl md:text-8xl lg:text-9xl font-black tracking-tighter transition-all duration-500 ease-out leading-none
                ${hoveredCity === city.id ? 'text-acid translate-x-4 skew-x-12' : 'text-zinc-600 group-hover:text-zinc-400'}
              `}
            >
              {city.name}
            </span>
            
            <div className={`
              opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center gap-4 flex-shrink-0
            `}>
              <span className="font-mono text-xs text-acid hidden md:block whitespace-nowrap">
                [{city.coordinates.lat.toFixed(2)}, {city.coordinates.lng.toFixed(2)}]
              </span>
              <ArrowRight className="text-acid w-8 h-8 md:w-16 md:h-16 -rotate-45 group-hover:rotate-0 transition-transform duration-500 flex-shrink-0" />
            </div>

            {/* Hover Image Reveal - Pseudo-mask effect */}
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