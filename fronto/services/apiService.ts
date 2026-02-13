/**
 * API Service for communicating with the Nocturne backend
 * 
 * Data source priority:
 * 1. Backend API (if running)
 * 2. Supabase REST API (direct query with anon key)
 * 3. Local cache file (all_events.json)
 */

import { API_BASE_URL, CITIES } from '../constants';

const API_URL = API_BASE_URL;

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export interface BackendEvent {
  id: number;
  title: string;
  link: string;
  date: string;
  time: string;
  location: string;
  description: string;
  source: string;
  city_id: string;
  created_at?: string;
  updated_at?: string;
}

export interface BackendCity {
  id: string;
  name: string;
  slug: string;
  coordinates: {
    lat: number;
    lng: number;
  };
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  total_events: number;
  total_subscribers: number;
}

export interface SubscriptionResponse {
  id: number;
  email: string;
  city_id: string;
  created_at: string;
  is_active: boolean;
}

/**
 * Get health status of the API
 */
export async function getHealthStatus(): Promise<HealthStatus> {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get all available cities
 */
export async function getCities(): Promise<BackendCity[]> {
  // Try backend API first
  try {
    const response = await fetch(`${API_URL}/cities`);
    if (response.ok) {
      const data = await response.json();
      return data.cities;
    }
  } catch {
    // Backend not available, fall through
  }

  // Fallback to static cities
  return CITIES.map(c => ({
    id: c.id,
    name: c.name,
    slug: c.slug,
    coordinates: c.coordinates,
  }));
}

/**
 * Query Supabase REST API directly
 */
async function fetchEventsFromSupabase(cityId: string, limit: number = 100): Promise<BackendEvent[]> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    return [];
  }

  try {
    const today = new Date().toISOString().split('T')[0];
    const url = `${SUPABASE_URL}/rest/v1/events?city_id=eq.${encodeURIComponent(cityId)}&date=gte.${today}&order=date.asc&limit=${limit}`;

    const response = await fetch(url, {
      headers: {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
    });

    if (!response.ok) {
      console.warn(`Supabase query failed: ${response.status}`);
      return [];
    }

    const data = await response.json();
    if (!Array.isArray(data)) {
      console.warn('Supabase returned non-array response:', typeof data);
      return [];
    }
    return data.map((row: any) => ({
      id: row.id,
      title: row.title || '',
      link: row.link || '',
      date: row.date || '',
      time: row.time || 'TBA',
      location: row.location || '',
      description: row.description || '',
      source: row.source || 'unknown',
      city_id: row.city_id || cityId,
    }));
  } catch (error) {
    console.warn('Supabase fetch failed:', error);
    return [];
  }
}

/**
 * Load events from local cache file - FILTER OUT PAST EVENTS
 */
async function loadEventsFromCache(cityId: string): Promise<BackendEvent[]> {
  try {
    const response = await fetch('/all_events.json');
    if (!response.ok) {
      return [];
    }
    
    const data = await response.json();
    
    // Get today's date in YYYY-MM-DD format for comparison
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = today.toISOString().split('T')[0];
    
    let cityEvents: any[] = [];
    
    // Try to get events for specific city from nested structure
    if (data.cities && data.cities[cityId]) {
      cityEvents = data.cities[cityId].events || [];
    } else if (data.events) {
      // Fallback: try root level events and filter by city
      cityEvents = data.events.filter((event: any) => event.city === cityId || event.city_id === cityId);
    }
    
    // Filter out past events (keep today and future)
    const futureEvents = cityEvents.filter((event: any) => {
      if (!event.date) return false;
      return event.date >= todayStr;
    });
    
    return futureEvents.map((event: any, index: number) => ({
      id: index + 1,
      title: event.title,
      link: event.link,
      date: event.date,
      time: event.time || 'TBA',
      location: event.location,
      description: event.description || '',
      source: event.source || 'unknown',
      city_id: cityId,
    }));
  } catch (error) {
    console.warn('Failed to load events from cache:', error);
    return [];
  }
}

/**
 * Get events for a specific city
 * Tries: Backend API → Supabase direct → Local cache
 */
export async function getCityEvents(
  cityId: string,
  startDate?: string,
  endDate?: string,
  limit: number = 100,
): Promise<BackendEvent[]> {
  // 1. Try backend API
  try {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await fetch(`${API_URL}/events/${cityId}?${params}`);
    if (response.ok) {
      const data = await response.json();
      if (Array.isArray(data)) {
        return data;
      }
    }
  } catch {
    // Backend not available
  }

  // 2. Try Supabase direct
  const supabaseEvents = await fetchEventsFromSupabase(cityId, limit);
  if (supabaseEvents.length > 0) {
    console.log(`[Supabase] Loaded ${supabaseEvents.length} events for ${cityId}`);
    return supabaseEvents;
  }

  // 3. Try local cache (already filtered for future events)
  const cachedEvents = await loadEventsFromCache(cityId);
  if (cachedEvents.length > 0) {
    // Apply the same filters as the API call to cached data
    let filteredEvents = cachedEvents;
    if (startDate) {
      const start = new Date(startDate);
      filteredEvents = filteredEvents.filter(event => new Date(event.date) >= start);
    }
    if (endDate) {
      const end = new Date(endDate);
      filteredEvents = filteredEvents.filter(event => new Date(event.date) <= end);
    }
    console.log(`[Cache] Loaded ${cachedEvents.length} future events for ${cityId}`);
    return filteredEvents.slice(0, limit);
  }

  return [];
}

/**
 * Trigger scraping for a specific city
 */
export async function scrapeCity(cityId: string): Promise<{ message: string; city_id: string }> {
  const response = await fetch(`${API_URL}/scrape/${cityId}`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to trigger scrape: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Trigger scraping for all cities
 */
export async function scrapeAllCities(): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/scrape/all`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to trigger scrape all: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Subscribe to email updates for a city
 */
export async function subscribeToCity(
  email: string,
  cityId: string
): Promise<SubscriptionResponse> {
  const response = await fetch(`${API_URL}/subscribe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, city_id: cityId }),
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Subscription failed');
  }
  
  return response.json();
}

/**
 * Format backend event to frontend event format
 */
export function formatBackendEvent(backendEvent: BackendEvent) {
  return {
    id: backendEvent.id.toString(),
    title: backendEvent.title,
    location: backendEvent.location || 'Location TBA',
    date: formatDate(backendEvent.date),
    time: backendEvent.time || 'TBA',
    description: backendEvent.description || 'Description not available',
    tags: [backendEvent.source, 'Event'],
    price: 'Free',
    imageUrl: `https://picsum.photos/600/400?random=${backendEvent.id}`,
    link: backendEvent.link,
    source: backendEvent.source,
  };
}

/**
 * Format date from backend to frontend format
 * FIXED: Use UTC dates to avoid timezone offset issues
 */
function formatDate(dateStr: string): string {
  try {
    if (!dateStr) return dateStr;
    
    // Parse the date string as UTC (YYYY-MM-DD)
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed
    const day = parseInt(parts[2], 10);
    
    // Create date in UTC to avoid timezone issues
    const date = new Date(Date.UTC(year, month, day));
    
    if (isNaN(date.getTime())) {
      return dateStr;
    }
    
    // Get today's date in UTC
    const now = new Date();
    const today = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    
    // Get tomorrow's date in UTC
    const tomorrow = new Date(today);
    tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);

    // Compare timestamps
    const dateTime = date.getTime();
    const todayTime = today.getTime();
    const tomorrowTime = tomorrow.getTime();

    if (dateTime === todayTime) {
      return 'Tonight';
    } else if (dateTime === tomorrowTime) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        timeZone: 'UTC'
      });
    }
  } catch {
    return dateStr;
  }
}
