/**
 * API Service for communicating with the Nocturne backend
 */

import { API_BASE_URL } from '../constants';

const API_URL = API_BASE_URL;

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
  const response = await fetch(`${API_URL}/cities`);
  if (!response.ok) {
    throw new Error(`Failed to fetch cities: ${response.statusText}`);
  }
  const data = await response.json();
  return data.cities;
}

/**
 * Get events for a specific city with retry logic
 * @param cityId - The backend city ID (e.g., 'ca--los-angeles')
 * @param startDate - Optional start date filter
 * @param endDate - Optional end date filter
 * @param limit - Maximum number of events to return (default: 100)
 * @param retries - Number of retry attempts (default: 3)
 */
export async function getCityEvents(
  cityId: string,
  startDate?: string,
  endDate?: string,
  limit: number = 100,
  retries: number = 3
): Promise<BackendEvent[]> {
  for (let i = 0; i < retries; i++) {
    try {
      const params = new URLSearchParams({ limit: limit.toString() });

      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await fetch(`${API_URL}/events/${cityId}?${params}`);

      if (!response.ok) {
        if (response.status === 404) {
          return []; // No events found for this city
        }
        if (response.status >= 500 && i < retries - 1) {
          // Server error, retry after delay
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
          continue;
        }
        throw new Error(`Failed to fetch events: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      if (i === retries - 1) throw error;
      // Retry after delay
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
  throw new Error('Max retries exceeded');
}

/**
 * Trigger scraping for a specific city
 * @param cityId - The backend city ID
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
 * @param email - User's email address
 * @param cityId - The backend city ID
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
    price: 'Free', // Default price, could be enhanced
    imageUrl: `https://picsum.photos/600/400?random=${backendEvent.id}`,
    link: backendEvent.link,
    source: backendEvent.source,
  };
}

/**
 * Format date from backend to frontend format
 */
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      return dateStr;
    }
    
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    // Reset time to compare dates only
    today.setHours(0, 0, 0, 0);
    tomorrow.setHours(0, 0, 0, 0);
    date.setHours(0, 0, 0, 0);

    if (date.getTime() === today.getTime()) {
      return 'Tonight';
    } else if (date.getTime() === tomorrow.getTime()) {
      return 'Tomorrow';
    } else {
      // Format as "Mon, Jan 15"
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
      });
    }
  } catch {
    return dateStr;
  }
}
