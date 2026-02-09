# Sorting Optimization Guide

## Overview

To improve performance, redundant sorting operations have been removed. The database now handles sorting once at query time, and this order is maintained throughout the application.

## What Changed

### 1. Database Level (Primary Sort)

**Location**: `backend/database.py`

The database queries now include `ORDER BY` clauses, ensuring events are sorted once at the source:

```python
# Events returned pre-sorted by date (ascending), then time
query = query.order_by(Event.date.asc(), Event.time.asc())
```

**Functions that return pre-sorted results:**
- `get_future_events_for_city()` - Returns events sorted by date
- `get_upcoming_events()` - Returns events sorted by date
- Database queries in API endpoints - Return events sorted by date

### 2. Frontend Level (Conditional Sort)

**Location**: `fronto/components/EventFilterBar.tsx`

The frontend now skips sorting when the data is already in the correct order:

```typescript
// Skip sorting when default "date-asc" is selected
// (database already returns events sorted by date ascending)
if (sort.by !== 'date' || !sort.ascending) {
  filtered = sortEvents(filtered, sort);
}
```

**Behavior:**
- Default view (Date: Soonest): No sorting needed ✓
- Date: Latest: Sort applied (reverse order)
- Price/Title/Quality: Sort applied (different criteria)

### 3. API Level (Efficient Queries)

**Location**: `backend/api/locations_router.py`

API endpoints query sorted data directly:

```python
# Query already returns sorted results
result = await db.execute(
    select(Event)
    .where(Event.date >= today)
    .order_by(Event.date, Event.time)  # Sort at database level
    .limit(limit)
)
```

### 4. Weekly Digest (No Redundant Sort)

**Location**: `backend/weekly_digest.py`

The digest script uses pre-sorted events from the database:

```python
# get_future_events_for_city returns events already sorted by date
events = await get_future_events_for_city(...)
# No additional sorting needed - events are ready to use
```

## Where Sorting Still Happens

### Necessary Sorting (Frontend)

**When user changes sort criteria:**
- Sort by Price (Low/High)
- Sort by Title (A-Z/Z-A)
- Sort by Quality (Premium/Standard)
- Sort by Date: Latest (reverse order)

**File**: `fronto/utils/eventFiltering.ts`

### Necessary Sorting (Backend)

**When criteria differs from database order:**
- Sort by distance (for proximity queries)
- Sort by population (for city listings)
- Sort by relevance (for search results)

### Necessary Sorting (Scraper)

**During data collection:**
- Events from multiple sources are sorted before saving to JSON
- This ensures consistent JSON file structure

**File**: `scraper/run.py` (line 272)

## Performance Benefits

### Before Optimization
```
1. Database: Query events (unsorted)
2. Database: Sort events (O(n log n))
3. API: Return events
4. Frontend: Receive events
5. Frontend: Sort events again (O(n log n)) ← REDUNDANT
```

### After Optimization
```
1. Database: Query and sort events (O(n log n))
2. API: Return pre-sorted events
3. Frontend: Use as-is (O(1)) ← EFFICIENT
4. Frontend: Sort only if user changes criteria
```

### Estimated Savings

For a city with 100 events:
- **Before**: ~2 sorting operations per page load
- **After**: 0 sorting operations (default view)
- **Savings**: ~50% reduction in sorting overhead

## Best Practices

### When Adding New Queries

1. **Always use `ORDER BY` in database queries:**
   ```python
   # Good
   query = select(Event).order_by(Event.date, Event.time)
   
   # Bad (requires sorting elsewhere)
   query = select(Event)
   ```

2. **Document sort order in function docstrings:**
   ```python
   async def get_events():
       """
       Returns events sorted by date (ascending), then time.
       No additional sorting needed by caller.
       """
   ```

3. **Skip redundant sorts:**
   ```typescript
   // Good - skip if already in correct order
   if (sort.by !== 'date' || !sort.ascending) {
       events = sortEvents(events, sort);
   }
   
   // Bad - always sorts
   events = sortEvents(events, sort);
   ```

### When to Sort

| Scenario | Action | Reason |
|----------|--------|--------|
| Database query | Add `ORDER BY` | Single sort at source |
| Default view (date asc) | Skip sort | Already sorted |
| User selects different criteria | Sort | Different order needed |
| Multiple data sources | Sort | Combine & order |
| Display by distance | Sort | Calculate then sort |

## Testing

### Verify Optimization

1. **Check database queries include ORDER BY:**
   ```python
   # Should see ORDER BY in SQL logs
   query = select(Event).order_by(Event.date, Event.time)
   ```

2. **Verify frontend skips default sort:**
   ```typescript
   // Add console.log to verify
   if (sort.by !== 'date' || !sort.ascending) {
       console.log('Sorting by:', sort.by);
       filtered = sortEvents(filtered, sort);
   } else {
       console.log('Skipping redundant sort');
   }
   ```

3. **Monitor performance:**
   - Before: Sorting visible in performance profiles
   - After: No sorting for default views

## Migration Notes

### Existing Code

If you have existing code that sorts events, check if it's redundant:

```python
# Old code (redundant)
events = await get_events(city_id)
events.sort(key=lambda x: x.date)  # ← REDUNDANT

# New code (efficient)
events = await get_events(city_id)  # Already sorted
```

```typescript
// Old code (redundant)
const events = await fetchEvents(cityId);
events.sort((a, b) => new Date(a.date) - new Date(b.date));  // ← REDUNDANT

// New code (efficient)
const events = await fetchEvents(cityId);  // Already sorted
```

## Files Modified

1. `backend/database.py` - Added ORDER BY to queries
2. `backend/api/locations_router.py` - Query sorted data, filter past events
3. `backend/weekly_digest.py` - Use pre-sorted events
4. `fronto/components/EventFilterBar.tsx` - Skip redundant sort

## Summary

The optimization ensures:
- ✅ Events sorted once at database level
- ✅ No redundant sorting in frontend (default view)
- ✅ No redundant sorting in backend scripts
- ✅ Sorting only when user requests different order
- ✅ Maintains functionality for all sort criteria
- ✅ Better performance with large event lists

Part of the Nocturne Event Platform.
