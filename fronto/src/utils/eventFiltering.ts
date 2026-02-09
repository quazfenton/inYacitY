/**
 * Event Filtering and Sorting Utilities
 * 
 * Supports 2D tagging system:
 * - Dimension 1: Price tier (free, paid)
 * - Dimension 2: Category (concert, nightlife, etc.)
 */

export interface EventTags {
  price_tier: number | string;
  category: string;
  custom_tags?: string[];
}

export interface Event {
  id: string;
  title: string;
  date: string;
  time?: string;
  location: string;
  price: number;
  tags: EventTags;
  source: string;
  quality_tier?: string;
  verified?: boolean;
  event_type?: string;
  image?: {
    url?: string;
    thumbnail_url?: string;
  };
  host?: {
    name: string;
    verified?: boolean;
  };
}

export interface EventFilter {
  price_tiers?: number[];
  categories?: string[];
  sources?: string[];
  quality_tiers?: string[];
  verifiedOnly?: boolean;
  featuredOnly?: boolean;
  excludeUserEvents?: boolean;
  excludeSources?: string[];
  dateFrom?: string;
  dateTo?: string;
  customTags?: string[];
  searchQuery?: string;
}

export interface SortOption {
  by: 'date' | 'price' | 'title' | 'quality';
  ascending: boolean;
}

/**
 * Price tier classifications
 */
export const PRICE_TIERS = {
  FREE: 0,
  UNDER_20: 20,
  UNDER_50: 50,
  UNDER_100: 100,
  PAID: 1000000
} as const;

/**
 * Event categories
 */
export const EVENT_CATEGORIES = {
  CONCERT: 'concert',
  NIGHTLIFE: 'nightlife',
  CLUB: 'club',
  FOOD: 'food',
  SPORTS: 'sports',
  THEATER: 'theater',
  ART: 'art',
  WORKSHOP: 'workshop',
  CONFERENCE: 'conference',
  SOCIAL: 'social',
  OTHER: 'other',
  UNTAGGED: ''
} as const;

/**
 * Get human-readable price tier name
 */
export function getPriceTierName(tier: number | string): string {
  const tierNum = typeof tier === 'string' ? parseInt(tier) : tier;
  
  switch (tierNum) {
    case PRICE_TIERS.FREE:
      return 'Free';
    case PRICE_TIERS.UNDER_20:
      return 'Under $20';
    case PRICE_TIERS.UNDER_50:
      return 'Under $50';
    case PRICE_TIERS.UNDER_100:
      return 'Under $100';
    case PRICE_TIERS.PAID:
      return 'All Paid';
    default:
      return 'Free';
  }
}

/**
 * Determine price tier from price amount
 */
export function determinePriceTier(priceInCents: number): number {
  if (priceInCents === 0) return PRICE_TIERS.FREE;
  if (priceInCents <= 2000) return PRICE_TIERS.UNDER_20;
  if (priceInCents <= 5000) return PRICE_TIERS.UNDER_50;
  if (priceInCents <= 10000) return PRICE_TIERS.UNDER_100;
  return PRICE_TIERS.PAID;
}

/**
 * Format price for display
 */
export function formatPrice(priceInCents: number): string {
  if (priceInCents === 0) return 'Free';
  return `$${(priceInCents / 100).toFixed(2)}`;
}

/**
 * Check if event matches filter criteria
 */
export function eventMatchesFilter(event: Event, filter: EventFilter): boolean {
  // Price tier filter
  if (filter.price_tiers && filter.price_tiers.length > 0) {
    const eventTier = typeof event.tags.price_tier === 'string'
      ? parseInt(event.tags.price_tier)
      : event.tags.price_tier;
    
    if (!filter.price_tiers.includes(eventTier)) {
      return false;
    }
  }
  
  // Category filter
  if (filter.categories && filter.categories.length > 0) {
    if (!filter.categories.includes(event.tags.category)) {
      return false;
    }
  }
  
  // Source filter
  if (filter.sources && filter.sources.length > 0) {
    if (!filter.sources.includes(event.source)) {
      return false;
    }
  }
  
  // Exclude sources
  if (filter.excludeSources && filter.excludeSources.length > 0) {
    if (filter.excludeSources.includes(event.source)) {
      return false;
    }
  }
  
  // Quality tier filter
  if (filter.quality_tiers && filter.quality_tiers.length > 0) {
    if (!event.quality_tier || !filter.quality_tiers.includes(event.quality_tier)) {
      return false;
    }
  }
  
  // Verified filter
  if (filter.verifiedOnly && !event.verified) {
    return false;
  }
  
  // Date range filter
  if (filter.dateFrom && event.date < filter.dateFrom) {
    return false;
  }
  if (filter.dateTo && event.date > filter.dateTo) {
    return false;
  }
  
  // Custom tags filter
  if (filter.customTags && filter.customTags.length > 0) {
    const eventTags = event.tags.custom_tags || [];
    const hasMatch = filter.customTags.some(tag => eventTags.includes(tag));
    if (!hasMatch) {
      return false;
    }
  }
  
  // User events filter
  if (filter.excludeUserEvents && event.event_type === 'user_created') {
    return false;
  }
  
  // Search query filter
  if (filter.searchQuery) {
    const query = filter.searchQuery.toLowerCase();
    const matchTitle = event.title.toLowerCase().includes(query);
    const matchLocation = event.location.toLowerCase().includes(query);
    const matchHost = event.host?.name.toLowerCase().includes(query);
    
    if (!matchTitle && !matchLocation && !matchHost) {
      return false;
    }
  }
  
  return true;
}

/**
 * Filter events with criteria
 */
export function filterEvents(events: Event[], filter: EventFilter): Event[] {
  return events.filter(event => eventMatchesFilter(event, filter));
}

/**
 * Sort events by criteria
 */
export function sortEvents(events: Event[], sort: SortOption): Event[] {
  const sorted = [...events];
  
  switch (sort.by) {
    case 'date':
      sorted.sort((a, b) => {
        const dateA = new Date(a.date).getTime();
        const dateB = new Date(b.date).getTime();
        return sort.ascending ? dateA - dateB : dateB - dateA;
      });
      break;
    
    case 'price':
      sorted.sort((a, b) => {
        return sort.ascending ? a.price - b.price : b.price - a.price;
      });
      break;
    
    case 'title':
      sorted.sort((a, b) => {
        return sort.ascending
          ? a.title.localeCompare(b.title)
          : b.title.localeCompare(a.title);
      });
      break;
    
    case 'quality':
      const qualityOrder = {
        'premium': 4,
        'standard': 3,
        'unverified': 2,
        'user': 1
      };
      sorted.sort((a, b) => {
        const qA = qualityOrder[a.quality_tier as keyof typeof qualityOrder] || 0;
        const qB = qualityOrder[b.quality_tier as keyof typeof qualityOrder] || 0;
        return sort.ascending ? qA - qB : qB - qA;
      });
      break;
  }
  
  return sorted;
}

/**
 * Get event statistics from event list
 */
export function getEventStats(events: Event[]): {
  total: number;
  by_source: Record<string, number>;
  by_category: Record<string, number>;
  by_price_tier: Record<string, number>;
  free_count: number;
  paid_count: number;
} {
  const stats = {
    total: events.length,
    by_source: {} as Record<string, number>,
    by_category: {} as Record<string, number>,
    by_price_tier: {} as Record<string, number>,
    free_count: 0,
    paid_count: 0
  };
  
  for (const event of events) {
    // Source stats
    stats.by_source[event.source] = (stats.by_source[event.source] || 0) + 1;
    
    // Category stats
    const category = event.tags.category || 'untagged';
    stats.by_category[category] = (stats.by_category[category] || 0) + 1;
    
    // Price tier stats
    const tier = event.tags.price_tier.toString();
    stats.by_price_tier[tier] = (stats.by_price_tier[tier] || 0) + 1;
    
    // Free/paid count
    if (event.price === 0) {
      stats.free_count++;
    } else {
      stats.paid_count++;
    }
  }
  
  return stats;
}

/**
 * Get available categories from events
 */
export function getAvailableCategories(events: Event[]): string[] {
  const categories = new Set<string>();
  
  for (const event of events) {
    if (event.tags.category) {
      categories.add(event.tags.category);
    }
  }
  
  return Array.from(categories).sort();
}

/**
 * Get available sources from events
 */
export function getAvailableSources(events: Event[]): string[] {
  const sources = new Set<string>();
  
  for (const event of events) {
    sources.add(event.source);
  }
  
  return Array.from(sources).sort();
}

/**
 * Group events by date
 */
export function groupEventsByDate(events: Event[]): Record<string, Event[]> {
  const grouped: Record<string, Event[]> = {};
  
  for (const event of events) {
    if (!grouped[event.date]) {
      grouped[event.date] = [];
    }
    grouped[event.date].push(event);
  }
  
  return grouped;
}

/**
 * Get upcoming events
 */
export function getUpcomingEvents(events: Event[], days: number = 30): Event[] {
  const now = new Date();
  const futureDate = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
  
  return events.filter(event => {
    const eventDate = new Date(event.date);
    return eventDate >= now && eventDate <= futureDate;
  });
}
