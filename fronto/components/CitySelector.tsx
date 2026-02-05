import React, { useState } from 'react';
import { City } from '../types';
import { ArrowRight, Loader2 } from 'lucide-react';

interface CitySelectorProps {
  onSelect: (city: City) => void;
  cities: City[];
  initialLoad?: boolean;
}

const CitySelector: React.FC<CitySelectorProps> = ({ onSelect, cities, initialLoad = false }) => {
  const [hoveredCity, setHoveredCity] = useState<string | null>(null);

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
    <div className="h-screen w-full flex flex-col justify-center px-4 md:px-12 lg:px-24 bg-void text-concrete overflow-hidden relative">
      {/* Background Noise/Grid Effect could go here */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>

      <div className="z-10 flex flex-col gap-0">
        <h1 className="text-sm font-mono tracking-widest text-zinc-500 mb-8 ml-1 uppercase">Select Sector</h1>
        
        {cities.map((city) => (
          <button
            key={city.id}
            onMouseEnter={() => setHoveredCity(city.id)}
            onMouseLeave={() => setHoveredCity(null)}
            onClick={() => onSelect(city)}
            className="group relative flex items-center justify-between w-full text-left focus:outline-none py-2 border-b border-concrete hover:border-acid transition-colors duration-500"
          >
            <span 
              className={`
                text-5xl md:text-8xl lg:text-9xl font-black tracking-tighter transition-all duration-500 ease-out
                ${hoveredCity === city.id ? 'text-acid translate-x-4 skew-x-12' : 'text-zinc-600 group-hover:text-zinc-400'}
              `}
            >
              {city.name}
            </span>
            
            <div className={`
              opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center gap-4
            `}>
              <span className="font-mono text-xs text-acid hidden md:block">
                [{city.coordinates.lat.toFixed(2)}, {city.coordinates.lng.toFixed(2)}]
              </span>
              <ArrowRight className="text-acid w-8 h-8 md:w-16 md:h-16 -rotate-45 group-hover:rotate-0 transition-transform duration-500" />
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
      
      <div className="absolute bottom-12 left-12 font-mono text-xs text-zinc-600">
        NOCTURNE SYSTEM v2.0
      </div>
    </div>
  );
};

export default CitySelector;