import React, { useState, useEffect, useCallback } from 'react';
import CitySelector from './components/CitySelector';
import EventCard from './components/EventCard';
import EventDetailModal from './components/EventDetailModal';
import SubscribeForm from './components/SubscribeForm';
import VibeChart from './components/VibeChart';
import ErrorBoundary from './components/ErrorBoundary';
import AmbientMusic from './components/AmbientMusic';
import EventFilterBar from './components/EventFilterBar';
import ScrollHelper from './components/ScrollHelper';
import { City, Event, ViewState, VibeData } from './types';
import { ArrowLeft, Sparkles, X, Loader2 } from 'lucide-react';
import {
  getCityEvents,
  getCities,
  formatBackendEvent,
  scrapeCity,
  getScrapeStatus,
  getCityEventCount,
  type BackendCity,
  type BackendEvent
} from './services/apiService';

const AUTO_SCRAPES_THRESHOLD = 3;

const App: React.FC = () => {
  const [view, setView] = useState<ViewState>(ViewState.LANDING);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [filteredEvents, setFilteredEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [cities, setCities] = useState<City[]>([]);
  const [initialLoad, setInitialLoad] = useState(true);
  const [vibeData, setVibeData] = useState<VibeData[]>([]);
  const [cooldownUntil, setCooldownUntil] = useState<Date | null>(null);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);
  const [initialEventCount, setInitialEventCount] = useState(0);
  const [newEventsCount, setNewEventsCount] = useState(0);
  
  // Modal state - managed at App level
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [modalInitialTab, setModalInitialTab] = useState<'details' | 'rsvp' | 'comments'>('details');

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

  // ESC key handler for modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedEvent) {
        setSelectedEvent(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedEvent]);

  // Cooldown countdown timer
  useEffect(() => {
    if (!cooldownUntil) return;
    const interval = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((cooldownUntil.getTime() - Date.now()) / 1000));
      setCooldownSeconds(remaining);
      if (remaining <= 0) {
        setCooldownUntil(null);
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldownUntil]);

  // Handle City Selection
  const handleCitySelect = async (city: City) => {
    setSelectedCity(city);
    setLoading(true);
    setView(ViewState.CITY_FEED);
    setNewEventsCount(0);
    setCooldownUntil(null);
    setCooldownSeconds(0);
    window.scrollTo(0, 0);

    try {
      // Fetch events from API
      const backendEvents: BackendEvent[] = await getCityEvents(city.id);

      // Format events for frontend
      const formattedEvents = backendEvents.map(formatBackendEvent);
      setEvents(formattedEvents);
      setFilteredEvents(formattedEvents);
      setInitialEventCount(formattedEvents.length);

      // Auto-trigger scrape if < 3 events
      if (formattedEvents.length < AUTO_SCRAPES_THRESHOLD) {
        console.log(`[auto-scrape] ${city.id} has ${formattedEvents.length} events (< ${AUTO_SCRAPES_THRESHOLD}), triggering scrape`);

        // Start scrape in background
        scrapeCity(city.id).catch(() => {});

        // Poll for new events with progressive loading
        let pollAttempts = 0;
        const maxAttempts = 30;
        let currentCount = formattedEvents.length;

        while (pollAttempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1500));

          try {
            const updatedEvents = await getCityEvents(city.id);
            const formatted = updatedEvents.map(formatBackendEvent);

            if (formatted.length > currentCount) {
              setEvents(formatted);
              setFilteredEvents(formatted);
              currentCount = formatted.length;
            }

            // Stop if no new events for 3 consecutive polls
            if (pollAttempts > 4 && formatted.length === currentCount) {
              break;
            }
          } catch {
            // Poll error, continue trying
          }

          pollAttempts++;
        }

        // Final fetch
        const finalEvents = await getCityEvents(city.id);
        const finalFormatted = finalEvents.map(formatBackendEvent);
        setEvents(finalFormatted);
        setFilteredEvents(finalFormatted);
        setInitialEventCount(finalFormatted.length);

        const newCount = Math.max(0, finalFormatted.length - formattedEvents.length);
        if (newCount > 0) {
          setNewEventsCount(newCount);
        }
      }

      // Fetch vibe data for the selected city
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
      setFilteredEvents([]);
      setInitialEventCount(0);
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
    setSelectedEvent(null);
    // Clear saved preference so next visit lands on home page
    localStorage.removeItem('inyacity_location_preference');
    localStorage.removeItem('inyacity_user_location');
    localStorage.removeItem('inyacity_location_cache');
  };

  // Open event modal
  const handleEventSelect = useCallback((event: Event, initialTab: 'details' | 'rsvp' | 'comments' = 'details') => {
    setModalInitialTab(initialTab);
    setSelectedEvent(event);
  }, []);

  // Close modal
  const handleCloseModal = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  // Refresh/Scrape Handler (per-city 30min cooldown)
  const handleRefreshEvents = async () => {
    if (!selectedCity || cooldownUntil) return;
    setLoading(true);

    try {
      const result = await scrapeCity(selectedCity.id);

      if (result.status === 'cooldown') {
        const mins = result.cooldown_remaining_minutes || 30;
        const until = new Date(Date.now() + mins * 60 * 1000);
        setCooldownUntil(until);
        setCooldownSeconds(Math.ceil(mins * 60));
        return;
      }

      // Poll for new events with progressive loading
      let currentCount = events.length;
      let pollAttempts = 0;
      const maxAttempts = 20;
      let finalEvents: Event[] = [];

      while (pollAttempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000));

        const backendEvents = await getCityEvents(selectedCity.id);
        finalEvents = backendEvents.map(formatBackendEvent);

        if (finalEvents.length > currentCount) {
          setEvents(finalEvents);
          currentCount = finalEvents.length;
        }

        if (pollAttempts > 2 && finalEvents.length === currentCount) {
          break;
        }

        pollAttempts++;
      }

      setEvents(finalEvents);
      setFilteredEvents(finalEvents);

      const newCount = Math.max(0, finalEvents.length - initialEventCount);
      setNewEventsCount(newCount);

      // Set 30-minute cooldown
      const until = new Date(Date.now() + 30 * 60 * 1000);
      setCooldownUntil(until);
      setCooldownSeconds(30 * 60);
    } catch (error) {
      console.error('Failed to refresh events:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <AmbientMusic />
      <ScrollHelper />
      <div className="min-h-screen bg-void text-zinc-100 selection:bg-acid selection:text-void font-sans">

        {/* Persistent Nav/Header — hidden on city feed so RETURN_TO_MAP is unobstructed */}
        {view !== ViewState.CITY_FEED && (
        <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-6 py-4 mix-blend-difference text-white pointer-events-none">
          <div className="font-mono font-bold tracking-tighter text-xl pointer-events-auto cursor-pointer" onClick={() => setShowAbout(true)}>
            NOCTURNE<span className="text-acid">///</span>
          </div>
          <div className="text-xs font-mono hidden md:block">
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()}
          </div>
        </nav>
        )}

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

        {/* Event Detail Modal - Single instance at App level */}
        {selectedEvent && (
          <EventDetailModal
            event={selectedEvent}
            isOpen={true}
            initialTab={modalInitialTab}
            onClose={handleCloseModal}
          />
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
                         disabled={loading || !!cooldownUntil}
                         className={`w-full py-4 border transition-all duration-300 font-mono text-sm flex items-center justify-center gap-2 ${
                           cooldownUntil
                             ? 'border-zinc-700 opacity-40 cursor-not-allowed'
                             : 'border-zinc-700 hover:border-acid hover:bg-acid hover:text-void'
                         } disabled:opacity-50 disabled:cursor-not-allowed`}
                       >
                          {loading ? (
                            <span className="animate-pulse">REFRESHING EVENTS...</span>
                          ) : cooldownUntil ? (
                            <>
                              <Sparkles size={16} />
                              COOLDOWN {Math.floor(cooldownSeconds / 60)}:{String(cooldownSeconds % 60).padStart(2, '0')}
                            </>
                          ) : (
                            <>
                              <Sparkles size={16} />
                              SCRAPE LIVE
                            </>
                          )}
                       </button>
                       <p className="text-[10px] text-zinc-600 mt-2 text-center font-mono">
                         {cooldownUntil && newEventsCount > 0 ? (
                           <>Found <span className="text-acid font-bold">{newEventsCount}</span> new events from live scrape.</>
                         ) : cooldownUntil ? (
                           <>Next refresh available when timer expires.</>
                         ) : (
                           <>* Fetches latest events from Eventbrite, Meetup & Luma.</>
                         )}
                       </p>
                     </div>
                  </div>
                </div>

                {/* Right Column: Events Feed */}
                 <div className="lg:col-span-8 space-y-6">
                    {/* Event Filter Bar */}
                    <EventFilterBar 
                      events={events} 
                      onFilterChange={setFilteredEvents}
                    />

                    {/* Events Count */}
                    <div className="flex items-center justify-between text-xs font-mono text-zinc-500">
                      <span>
                        {filteredEvents.length} {filteredEvents.length === 1 ? 'EVENT' : 'EVENTS'}
                        {filteredEvents.length !== events.length && ` (of ${events.length})`}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-6">
                       {loading && events.length === 0 ? (
                         <div className="py-20 text-center border border-zinc-800 border-dashed text-zinc-600 font-mono animate-pulse">
                           SCANNING FOR EVENTS...
                         </div>
                       ) : loading && events.length > 0 && events.length < AUTO_SCRAPES_THRESHOLD ? (
                         <>
                           {filteredEvents.map((event, idx) => (
                             <div
                               key={event.id}
                               className="animate-slide-in-up"
                               style={{
                                 animation: `slideInUp 0.6s ease-out forwards`,
                                 animationDelay: `${idx * 120}ms`
                               }}
                             >
                               <EventCard event={event} onSelect={handleEventSelect} />
                             </div>
                           ))}
                           <div className="py-20 text-center border border-acid/30 border-dashed text-acid font-mono animate-pulse">
                             <div className="flex items-center justify-center gap-3">
                               <Loader2 className="animate-spin w-5 h-5" />
                               SCRAPING LIVE — FOUND {events.length} EVENT{events.length !== 1 ? 'S' : ''} SO FAR...
                             </div>
                           </div>
                         </>
                       ) : loading && events.length > 0 ? (
                         <>
                           {filteredEvents.map((event, idx) => (
                             <div
                               key={event.id}
                               className="animate-slide-in-up"
                               style={{
                                 animation: `slideInUp 0.6s ease-out forwards`,
                                 animationDelay: `${idx * 120}ms`
                               }}
                             >
                               <EventCard event={event} onSelect={handleEventSelect} />
                             </div>
                           ))}
                           <div className="py-20 text-center border border-acid/30 border-dashed text-acid font-mono animate-pulse">
                             LOADING MORE EVENTS...
                           </div>
                         </>
                       ) : filteredEvents.length === 0 ? (
                         <div className="py-20 text-center border border-zinc-800 border-dashed text-zinc-600 font-mono">
                           {events.length === 0
                             ? 'NO EVENTS FOUND. TRY REFRESHING.'
                             : 'NO EVENTS MATCH YOUR FILTERS.'
                           }
                         </div>
                       ) : (
                         filteredEvents.map((event, idx) => (
                           <div
                             key={event.id}
                             className="animate-slide-in-up"
                             style={{
                               animationDelay: `${idx * 120}ms`,
                               opacity: 0,
                               animation: `slideInUp 0.6s ease-out forwards`,
                               animationDelay: `${idx * 120}ms`
                             }}
                           >
                             <EventCard event={event} onSelect={handleEventSelect} />
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