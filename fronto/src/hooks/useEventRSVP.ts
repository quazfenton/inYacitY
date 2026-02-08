/**
 * React hook for event RSVP and calendar integration
 * Handles RSVP to events with optional Google/Apple Calendar integration
 * and optional 2-hour reminder notifications
 */

import { useState, useCallback } from 'react';

interface RSVPResponse {
  success: boolean;
  rsvp_id: string;
  calendar_url?: string;
  message: string;
  reminder_enabled: boolean;
  timestamp: string;
}

interface EventData {
  event_id: string;
  title: string;
  date: string; // YYYY-MM-DD
  time?: string; // HH:MM or "HH:MM AM/PM" or "TBA"
  location: string;
  description?: string;
}

interface RSVPData {
  user_name: string;
  user_email?: string;
  calendar_type?: 'google' | 'apple' | null;
  reminder_enabled?: boolean;
  reminder_minutes?: number;
}

interface RSVPStatus {
  rsvp_count: number;
  attendees: Array<{
    name: string;
    email?: string;
    rsvp_id: string;
  }>;
}

export function useEventRSVP() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rsvpData, setRsvpData] = useState<RSVPResponse | null>(null);

  /**
   * RSVP to an event
   */
  const rsvpEvent = useCallback(
    async (event: EventData, rsvp: RSVPData): Promise<RSVPResponse | null> => {
      setIsLoading(true);
      setError(null);

      try {
        // Validate required fields
        if (!event.event_id || !event.title || !event.date || !event.location) {
          throw new Error('Missing required event fields');
        }

        if (!rsvp.user_name) {
          throw new Error('User name is required');
        }

        // Prepare request payload
        const payload = {
          event_id: event.event_id,
          title: event.title,
          date: event.date,
          time: event.time || 'TBA',
          location: event.location,
          description: event.description || '',
          user_name: rsvp.user_name,
          user_email: rsvp.user_email || '',
          calendar_type: rsvp.calendar_type || null,
          reminder_enabled: rsvp.reminder_enabled ?? false,
          reminder_minutes: rsvp.reminder_minutes ?? 120,
        };

        // Send RSVP request
        const response = await fetch('/api/scraper/rsvp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = (await response.json()) as RSVPResponse;

        if (!response.ok) {
          throw new Error(data.message || 'RSVP failed');
        }

        setRsvpData(data);

        // Redirect to calendar URL if provided
        if (data.calendar_url) {
          window.open(data.calendar_url, '_blank');
        }

        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to RSVP';
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Cancel RSVP
   */
  const cancelRSVP = useCallback(
    async (rsvpId: string): Promise<boolean> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/scraper/rsvp/${rsvpId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          throw new Error('Failed to cancel RSVP');
        }

        setRsvpData(null);
        return true;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to cancel RSVP';
        setError(errorMessage);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Get RSVP status for an event
   */
  const getRSVPStatus = useCallback(
    async (eventId: string): Promise<RSVPStatus | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/scraper/rsvp-status/${eventId}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.message || 'Failed to fetch RSVP status');
        }

        return {
          rsvp_count: data.rsvp_count,
          attendees: data.attendees,
        };
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to fetch RSVP status';
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return {
    rsvpEvent,
    cancelRSVP,
    getRSVPStatus,
    isLoading,
    error,
    rsvpData,
  };
}

/**
 * Component example:
 *
 * export function EventRSVPButton({ event }: { event: EventData }) {
 *   const { rsvpEvent, isLoading, error } = useEventRSVP();
 *   const [showForm, setShowForm] = useState(false);
 *
 *   const handleRSVP = async (userName: string) => {
 *     const success = await rsvpEvent(event, {
 *       user_name: userName,
 *       calendar_type: 'google',
 *       reminder_enabled: true,
 *       reminder_minutes: 120,
 *     });
 *
 *     if (success) {
 *       setShowForm(false);
 *       // Show success message
 *     }
 *   };
 *
 *   return (
 *     <div>
 *       <button onClick={() => setShowForm(!showForm)}>
 *         {showForm ? 'Cancel' : 'RSVP to Event'}
 *       </button>
 *
 *       {showForm && (
 *         <form onSubmit={(e) => {
 *           e.preventDefault();
 *           const name = (e.target as HTMLFormElement).name.value;
 *           handleRSVP(name);
 *         }}>
 *           <input
 *             name="name"
 *             placeholder="Your name"
 *             required
 *           />
 *           <label>
 *             <input type="checkbox" name="calendar" defaultChecked />
 *             Add to Google Calendar
 *           </label>
 *           <label>
 *             <input type="checkbox" name="reminder" defaultChecked />
 *             Send 2-hour reminder
 *           </label>
 *           <button type="submit" disabled={isLoading}>
 *             {isLoading ? 'RSVPing...' : 'RSVP'}
 *           </button>
 *         </form>
 *       )}
 *
 *       {error && <p style={{ color: 'red' }}>{error}</p>}
 *     </div>
 *   );
 * }
 */
