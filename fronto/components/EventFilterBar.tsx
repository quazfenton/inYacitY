import React, { useState, useEffect } from 'react';
import { Event, EventFilter, SortOption, PRICE_TIERS, EVENT_CATEGORIES, getPriceTierName, filterEvents, sortEvents } from '../src/utils/eventFiltering';
import { Filter, X, ChevronDown } from 'lucide-react';

interface EventFilterBarProps {
  events: Event[];
  onFilterChange: (filteredEvents: Event[]) => void;
}

const EventFilterBar: React.FC<EventFilterBarProps> = ({ events, onFilterChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [filter, setFilter] = useState<EventFilter>({});
  const [sort, setSort] = useState<SortOption>({ by: 'date', ascending: true });
  const [searchQuery, setSearchQuery] = useState('');

  // Apply filters whenever they change
  useEffect(() => {
    let filtered = [...events];

    // Apply search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(event =>
        event.title.toLowerCase().includes(query) ||
        event.location.toLowerCase().includes(query) ||
        event.description.toLowerCase().includes(query)
      );
    }

    // Apply other filters
    filtered = filterEvents(filtered, filter);

    // Apply sort only if not default (database already returns events sorted by date ascending)
    // Skip sorting when sort.by is 'date' and ascending is true (same as database order)
    if (sort.by !== 'date' || !sort.ascending) {
      filtered = sortEvents(filtered, sort);
    }

    onFilterChange(filtered);
  }, [events, filter, sort, searchQuery, onFilterChange]);

  const togglePriceTier = (tier: number) => {
    setFilter(prev => {
      const currentTiers = prev.price_tiers || [];
      const newTiers = currentTiers.includes(tier)
        ? currentTiers.filter(t => t !== tier)
        : [...currentTiers, tier];
      return { ...prev, price_tiers: newTiers };
    });
  };

  const toggleCategory = (category: string) => {
    setFilter(prev => {
      const currentCategories = prev.categories || [];
      const newCategories = currentCategories.includes(category)
        ? currentCategories.filter(c => c !== category)
        : [...currentCategories, category];
      return { ...prev, categories: newCategories };
    });
  };

  const toggleSource = (source: string) => {
    setFilter(prev => {
      const currentSources = prev.sources || [];
      const newSources = currentSources.includes(source)
        ? currentSources.filter(s => s !== source)
        : [...currentSources, source];
      return { ...prev, sources: newSources };
    });
  };

  const clearFilters = () => {
    setFilter({});
    setSearchQuery('');
    // Reset to default - no need to specify date-asc as database already sorts by date
    setSort({ by: 'date', ascending: true });
  };

  const hasActiveFilters = 
    (filter.price_tiers && filter.price_tiers.length > 0) ||
    (filter.categories && filter.categories.length > 0) ||
    (filter.sources && filter.sources.length > 0) ||
    !!searchQuery;

  // Get unique sources from events
  const sources = [...new Set(events.map(e => e.source).filter(Boolean))];

  return (
    <div className="border border-zinc-800 bg-black/50">
      {/* Header - Always visible */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search events..."
              className="w-full bg-zinc-900 border border-zinc-800 px-4 py-2 text-white font-mono text-sm focus:border-acid focus:outline-none transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Quick Sort */}
          <select
            value={`${sort.by}-${sort.ascending ? 'asc' : 'desc'}`}
            onChange={(e) => {
              const [by, order] = e.target.value.split('-');
              setSort({ by: by as SortOption['by'], ascending: order === 'asc' });
            }}
            className="bg-zinc-900 border border-zinc-800 px-3 py-2 text-white font-mono text-sm focus:border-acid focus:outline-none"
          >
            <option value="date-asc">Date: Soonest</option>
            <option value="date-desc">Date: Latest</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="title-asc">Title: A-Z</option>
            <option value="title-desc">Title: Z-A</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs font-mono text-zinc-500 hover:text-acid transition-colors"
            >
              CLEAR
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-mono border transition-colors ${
              isExpanded
                ? 'border-acid text-acid'
                : 'border-zinc-800 text-zinc-400 hover:border-zinc-600'
            }`}
          >
            <Filter size={14} />
            FILTERS
            {hasActiveFilters && (
              <span className="bg-acid text-void px-1.5 py-0.5 text-[10px]">
                ON
              </span>
            )}
            <ChevronDown
              size={14}
              className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="border-t border-zinc-800 p-4 space-y-6">
          {/* Price Tiers */}
          <div>
            <h4 className="text-xs font-mono text-zinc-500 mb-3 uppercase">Price</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(PRICE_TIERS).map(([name, value]) => (
                <button
                  key={name}
                  onClick={() => togglePriceTier(value)}
                  className={`px-3 py-1.5 text-xs font-mono border transition-colors ${
                    filter.price_tiers?.includes(value)
                      ? 'border-acid text-acid'
                      : 'border-zinc-800 text-zinc-400 hover:border-zinc-600'
                  }`}
                >
                  {getPriceTierName(value)}
                </button>
              ))}
            </div>
          </div>

          {/* Categories */}
          <div>
            <h4 className="text-xs font-mono text-zinc-500 mb-3 uppercase">Category</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(EVENT_CATEGORIES).map(([name, value]) => (
                value && (
                  <button
                    key={name}
                    onClick={() => toggleCategory(value)}
                    className={`px-3 py-1.5 text-xs font-mono border transition-colors ${
                      filter.categories?.includes(value)
                        ? 'border-acid text-acid'
                        : 'border-zinc-800 text-zinc-400 hover:border-zinc-600'
                    }`}
                  >
                    {name}
                  </button>
                )
              ))}
            </div>
          </div>

          {/* Sources */}
          {sources.length > 0 && (
            <div>
              <h4 className="text-xs font-mono text-zinc-500 mb-3 uppercase">Source</h4>
              <div className="flex flex-wrap gap-2">
                {sources.map((source) => (
                  <button
                    key={source}
                    onClick={() => toggleSource(source!)}
                    className={`px-3 py-1.5 text-xs font-mono border transition-colors capitalize ${
                      filter.sources?.includes(source!)
                        ? 'border-acid text-acid'
                        : 'border-zinc-800 text-zinc-400 hover:border-zinc-600'
                    }`}
                  >
                    {source}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EventFilterBar;
