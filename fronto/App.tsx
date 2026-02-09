import React, { useState, useEffect } from 'react';
import CitySelector from './components/CitySelector';
import EventCard from './components/EventCard';
import SubscribeForm from './components/SubscribeForm';
import VibeChart from './components/VibeChart';
import ErrorBoundary from './components/ErrorBoundary';
import AmbientMusic from './components/AmbientMusic';
import ScrollHelper from './components/ScrollHelper';
import { City, Event, ViewState, VibeData } from './types';
import { ArrowLeft, Sparkles, X } from 'lucide-react';
import {
  getCityEvents,
  getCities,
  formatBackendEvent,
  scrapeCity,
  type BackendCity,
  type BackendEvent
} from './services/apiService';

const App: React.FC = () => {
  const [view, setView] = useState<ViewState>(ViewState.LANDING);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [cities, setCities] = useState<City[]>([]);
  const [initialLoad, setInitialLoad] = useState(true);
  const [vibeData, setVibeData] = useState<VibeData[]>([]);
  const [refreshUsed, setRefreshUsed] = useState(false);
  const [initialEventCount, setInitialEventCount] = useState(0);
  const [newEventsCount, setNewEventsCount] = useState(0);

  // Load cities from API on mount
  useEffect(() => {
    const loadCities = async () => {
      try {
        const backendCities = await getCities();
        const frontendCities: City[] = backendCities.map(c => ({
          id: c.id,
          name: c.name,
          slug: c.slug,
          coordinates: c.coordinates,
        }));
        setCities(frontendCities);
        setInitialLoad(false);
      } catch (error) {
        console.error('Failed to load cities:', error);
        // Fallback to static cities if API fails
        const { CITIES } = await import('./constants');
        setCities(CITIES);
        setInitialLoad(false);
      }
    };
    loadCities();
  }, []);

  // Handle City Selection
  const handleCitySelect = async (city: City) => {
    setSelectedCity(city);
    setLoading(true);
    setView(ViewState.CITY_FEED);
    setNewEventsCount(0);
    window.scrollTo(0, 0);

    try {
      // Fetch events from API
      const backendEvents: BackendEvent[] = await getCityEvents(city.id);

      // Format events for frontend
      const formattedEvents = backendEvents.map(formatBackendEvent);
      setEvents(formattedEvents);
      setInitialEventCount(formattedEvents.length);
      
      // Fetch vibe data for the selected city
      // TODO: Implement API call to fetch actual vibe data
      // For now, using mock data as fallback
      const mockVibeData: VibeData[] = [
        { day: 'Mon', intensity: 40, crowd: 30 },
        { day: 'Tue', intensity: 60, crowd: 45 },
        { day: 'Wed', intensity: 35, crowd: 25 },
        { day: 'Thu', intensity: 75, crowd: 60 },
        { day: 'Fri', intensity: 90, crowd: 80 },
        { day: 'Sat', intensity: 85, crowd: 75 },
        { day: 'Sun', intensity: 50, crowd: 40 },
      ];
      setVibeData(mockVibeData);
    } catch (error) {
      console.error('Failed to load events:', error);
      setEvents([]);
      setInitialEventCount(0);
      // Set empty vibe data on error
      setVibeData([]);
    } finally {
      setLoading(false);
    }
  };

  // Back to Home
  const handleBack = () => {
    setView(ViewState.LANDING);
    setSelectedCity(null);
    setEvents([]);
  };

  // Refresh/Scrape Handler (limited to 1 per entire session)
  const handleRefreshEvents = async () => {
    if (!selectedCity || refreshUsed) return;
    setLoading(true);
    
    try {
      // Trigger scrape for this city
      await scrapeCity(selectedCity.id);
      
      // Poll for new events with progressive loading
      let currentCount = events.length;
      let pollAttempts = 0;
      const maxAttempts = 20; // Poll for up to 20 seconds
      let finalEvents: Event[] = [];
      
      while (pollAttempts < maxAttempts) {
        // Wait before polling
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Fetch updated events
        const backendEvents = await getCityEvents(selectedCity.id);
        finalEvents = backendEvents.map(formatBackendEvent);
        
        // If we got new events, update UI progressively
        if (finalEvents.length > currentCount) {
          setEvents(finalEvents);
          currentCount = finalEvents.length;
        }
        
        // Stop polling if we haven't seen new events in last 2 attempts
        if (pollAttempts > 2 && finalEvents.length === currentCount) {
          break;
        }
        
        pollAttempts++;
      }
      
      // Set final events
      setEvents(finalEvents);
      
      // Calculate new events
      const newCount = Math.max(0, finalEvents.length - initialEventCount);
      setNewEventsCount(newCount);
      
      // Mark refresh as used for this entire session (persists across cities)
      setRefreshUsed(true);
    } catch (error) {
      console.error('Failed to refresh events:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <ScrollHelper />
      <AmbientMusic />
      <div className="min-h-screen bg-void text-zinc-100 selection:bg-acid selection:text-void font-sans">

        {/* Persistent Nav/Header */}
        <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-6 py-4 mix-blend-difference text-white pointer-events-none">
          <div className="font-mono font-bold tracking-tighter text-xl pointer-events-auto cursor-pointer" onClick={() => setShowAbout(true)}>
            NOCTURNE<span className="text-acid">///</span>
          </div>
          <div className="text-xs font-mono hidden md:block">
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()}
          </div>
        </nav>

        {/* About Modal */}
        {showAbout && (
          <div className="fixed inset-0 z-[100] bg-void/90 backdrop-blur-md flex items-center justify-center p-6">
            <div className="max-w-lg w-full border border-zinc-800 bg-black p-8 relative">
              <button onClick={() => setShowAbout(false)} className="absolute top-4 right-4 text-zinc-500 hover:text-acid">
                <X />
              </button>
              <h2 className="text-2xl font-black mb-4">MANIFESTO</h2>
              <p className="font-mono text-sm text-zinc-400 mb-6 leading-relaxed">
                Nocturne is an automated curator for the underground. We scrape the deep web to find events that exist on the fringe.
                <br/><br/>
                Participate at your own risk.
              </p>
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <main className="relative">
          {view === ViewState.LANDING ? (
            <CitySelector onSelect={handleCitySelect} cities={cities} initialLoad={initialLoad} />
          ) : (
            <div className="min-h-screen">
              {/* City Header */}
              <header className="sticky top-0 z-40 bg-void/80 backdrop-blur-lg border-b border-zinc-800">
                 <div className="max-w-7xl mx-auto px-4 md:px-8 py-6 flex flex-col md:flex-row justify-between items-end gap-6">
                   <div>
                      <button
                        onClick={handleBack}
                        className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors mb-2 font-mono text-xs"
                      >
                        <ArrowLeft size={14} /> RETURN_TO_MAP
                      </button>
                      <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-none text-white">
                        {selectedCity?.name}
                      </h1>
                   </div>

                   <div className="w-full md:w-auto flex flex-col items-end gap-2">
                     <div className="flex items-center gap-2">
                        <div className="h-2 w-2 bg-acid rounded-full animate-pulse"></div>
                        <span className="font-mono text-xs text-acid">LIVE FEED ACTIVE</span>
                     </div>
                   </div>
                 </div>
              </header>

              <div className="max-w-7xl mx-auto px-4 md:px-8 py-12 grid grid-cols-1 lg:grid-cols-12 gap-12">

                {/* Left Column: Sidebar Info */}
                <div className="lg:col-span-4 space-y-12">
                  <div className="sticky top-40 space-y-8">
                    <div className="p-6 border border-zinc-800 bg-zinc-900/20">
                      <SubscribeForm cityId={selectedCity?.id} cityName={selectedCity?.name} />
                    </div>

                    <VibeChart data={vibeData} />

                    <div className="border-t border-zinc-800 pt-6">
                       <h3 className="font-mono text-xs text-zinc-500 mb-4 uppercase">Actions</h3>
                       <button
                         onClick={handleRefreshEvents}
                         disabled={loading || refreshUsed}
                         className={`w-full py-4 border transition-all duration-300 font-mono text-sm flex items-center justify-center gap-2 ${
                           refreshUsed
                             ? 'border-zinc-700 opacity-30 cursor-not-allowed'
                             : 'border-zinc-700 hover:border-acid hover:bg-acid hover:text-void'
                         } disabled:opacity-50 disabled:cursor-not-allowed`}
                       >
                          {loading ? (
                            <span className="animate-pulse">REFRESHING EVENTS...</span>
                          ) : refreshUsed ? (
                            <>
                              <Sparkles size={16} />
                              REFRESH USED (0/1)
                            </>
                          ) : (
                            <>
                              <Sparkles size={16} />
                              REFRESH EVENTS (1/1)
                            </>
                          )}
                       </button>
                       <p className="text-[10px] text-zinc-600 mt-2 text-center font-mono">
                         {refreshUsed && newEventsCount > 0 ? (
                           <>Found <span className="text-acid font-bold">{newEventsCount}</span> new events from live scrape.</>
                         ) : refreshUsed ? (
                           <>Refresh limit reached for this session.</>
                         ) : (
                           <>* Fetches latest events from Eventbrite, Meetup & Luma.</>
                         )}
                       </p>
                     </div>
                  </div>
                </div>

                {/* Right Column: Events Feed */}
                 <div className="lg:col-span-8">
                    <div className="grid grid-cols-1 gap-6">
                       {loading && events.length === 0 ? (
                         <div className="py-20 text-center border border-zinc-800 border-dashed text-zinc-600 font-mono animate-pulse">
                           SCANNING FOR EVENTS...
                         </div>
                       ) : loading && events.length > 0 ? (
                         <>
                           {events.map((event, idx) => (
                             <div 
                               key={event.id} 
                               className="animate-slide-in-up" 
                               style={{ 
                                 animation: `slideInUp 0.6s ease-out forwards`,
                                 animationDelay: `${idx * 120}ms`
                               }}
                             >
                               <EventCard event={event} />
                             </div>
                           ))}
                           <div className="py-20 text-center border border-acid/30 border-dashed text-acid font-mono animate-pulse">
                             LOADING MORE EVENTS...
                           </div>
                         </>
                       ) : events.length === 0 ? (
                         <div className="py-20 text-center border border-zinc-800 border-dashed text-zinc-600 font-mono">
                           NO EVENTS FOUND. TRY REFRESHING.
                         </div>
                       ) : (
                        events.map((event, idx) => (
                          <div 
                            key={event.id} 
                            className="animate-slide-in-up" 
                            style={{ 
                              opacity: 0,
                              animation: `slideInUp 0.6s ease-out forwards`,
                              animationDelay: `${idx * 120}ms`
                            }}
                          >
                            <EventCard event={event} />
                          </div>
                        ))
                      )}
                   </div>
                </div>

              </div>
            </div>
          )}
        </main>

        {/* Global Grain Overlay for "Aesthetic" */}
        <div className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-[9999]"
             style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default App;
