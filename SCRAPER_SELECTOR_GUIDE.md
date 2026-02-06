# Scraper Selector Optimization Guide

Comprehensive guide to CSS selectors, HTML structure, and parsing methods for each event source.

## Overview

This document provides:
- HTML structure analysis for each site
- Effective CSS selectors for data extraction
- Common parsing challenges and solutions
- Deduplication strategies
- Data quality metrics
- Site-specific notes and workarounds

## 1. Eventbrite

### Site Structure
- Modern JavaScript-heavy (React)
- Uses CSS-in-JS with generated class names
- Data often in `<script>` tags as JSON
- Requires JavaScript rendering

### Key Selectors

**Event Listings Page:**
```css
/* Event cards container */
div[data-testid="event-card"]
div[data-testid="search-results"] > div

/* Event title */
h3[data-testid="event-title"]
div[role="button"] > h3

/* Event link */
a[href*="/events/"]

/* Date/Time */
span[data-testid="event-date"]
div[class*="EventDateTime"]

/* Location */
span[data-testid="event-location"]
div[class*="Location"]

/* Price */
div[class*="PriceTag"]
span[data-testid="event-price"]
```

### Parsing Challenges

1. **Generated Class Names** - Use data-testid attributes instead
2. **Dynamic Content** - Requires wait_for_selector before scraping
3. **Lazy Loading** - Scroll to load more events
4. **JSON Data** - Check `<script type="application/ld+json">` for structured data

### Best Practices

```python
# Use data-testid attributes
await page.wait_for_selector('[data-testid="event-card"]')

# JSON-LD for structured data
script_tags = soup.find_all('script', type='application/ld+json')
for script in script_tags:
    data = json.loads(script.string)
    if data.get('@type') == 'Event':
        # Extract structured data
```

### Deduplication
- **Key:** Event URL (`href` attribute)
- **Method:** Hash of event URL to detect duplicates
- **Frequency:** Multiple pages may have same event

---

## 2. Meetup

### Site Structure
- Uses GraphQL API for data loading
- HTML contains minimal event data
- Event details often in tooltip/modal
- AJAX-based infinite scroll

### Key Selectors

**Event Card:**
```css
/* Event container */
div[class*="EventCard"]
a[data-event-id]

/* Title */
h3[class*="EventCardTitle"]
span[class*="EventName"]

/* Date/Time */
time[data-datetime]
span[class*="EventTime"]
span[data-test="event-date"]

/* Location */
span[class*="Location"]
span[data-test="location"]

/* RSVP/Attendance */
span[class*="Going"]
span[data-test="going-count"]

/* Event link */
a[href*="/events/"]
```

### Parsing Challenges

1. **AJAX Loading** - Need to wait for content load
2. **GraphQL Data** - Intercept API calls for structured data
3. **URL Format Variation** - Events have multiple URL formats
4. **Time Zone Issues** - Meetup uses user's timezone

### Best Practices

```python
# Wait for event cards to load
await page.wait_for_selector('[class*="EventCard"]')

# Scroll to load more events
await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')

# Intercept GraphQL API calls for better data
# Check network tab for /graphql endpoint

# Convert Meetup timestamp
from datetime import datetime
timestamp_ms = event_time_ms / 1000
date_obj = datetime.fromtimestamp(timestamp_ms)
```

### Deduplication
- **Key:** Event URL or event ID from GraphQL
- **Method:** Extract event ID from URL
- **Storage:** Use concurrent dict to track processed events

---

## 3. Luma

### Site Structure
- Vue.js framework
- Class names include content hash
- HTML structure is clean but uses utility classes
- Date headers separate event groups

### Key Selectors

**Event Cards:**
```css
/* Date header */
div.date-title
div.date
div.weekday

/* Event container */
div.content-card
div[class*="card"]

/* Title */
h3
span.text-ellipses

/* Link */
a[href^="/"]

/* Location icon/text */
div[class*="location"]
svg (look for location icon path)

/* Time */
span (contains time pattern \d{1,2}:\d{2})
```

### Parsing Challenges

1. **Hash-based Classes** - Use content-based selectors
2. **Event Structure** - Events grouped by date, need context
3. **Icon-based Data** - Location marked only by SVG icon
4. **Link Format** - Event IDs are slugs, not numeric

### Best Practices

```python
# Find events between date headers
date_headers = soup.find_all('div', class_='date-title')
for header in date_headers:
    date = parse_luma_date(header)
    
    # Find next date header
    next_header = header.find_next('div', class_='date-title')
    
    # Extract events between headers
    for card in header.find_next_siblings('div', class_='content-card'):
        if next_header and card == next_header:
            break

# Location detection by SVG path
location_paths = svg.find_all('path')
has_location_marker = any(
    'M2 6.854' in path.get('d', '')
    for path in location_paths
)
```

### Deduplication
- **Key:** Event URL (slug-based)
- **Method:** Store processed URL slugs
- **Format:** URLs like `/event-name-123abc`

---

## 4. Dice.fm

### Site Structure
- Uses styled-components
- Data in component props
- Event cards are clickable links
- Listing pages are straightforward

### Key Selectors

**Event Listings:**
```css
/* Event card link */
a[class*="EventCardLink"]
a[class*="event"]

/* Image */
img[alt]  /* Title in alt attribute */
img[srcset]

/* Title */
div[class*="Title"]
div[class*="title"]

/* Date */
div[class*="DateText"]
span[class*="date"]

/* Venue */
div[class*="Venue"]
span[class*="venue"]

/* Price info */
div[class*="price"]
span[class*="Price"]
```

### Parsing Challenges

1. **Image Alt Text** - Title often in image alt attribute
2. **Generated Classes** - Need fallback selectors
3. **Free Events Only** - Default filter on URL
4. **Price Detection** - "Free" vs actual price parsing

### Best Practices

```python
# Extract title from image alt text (fallback)
img = card.find('img')
title = img.get('alt', '')

# Use class partial matching
card.find('div', class_=re.compile(r'Title'))

# Parse free events URL format
url = f"{base_url}?priceTo=1"  # Free events
url = f"{base_url}?priceTo=2000"  # Under $20

# Price parsing
price_match = re.search(r'\$(\d+)', card.get_text())
price_cents = int(price_match.group(1)) * 100
```

### Deduplication
- **Key:** Event link (Dice.fm full URL)
- **Method:** Parse and hash event links
- **Note:** Query parameters may vary, normalize before comparing

---

## 5. RA.co

### Site Structure
- Next.js application
- Clean semantic HTML
- Good data-testid attributes
- JSON-LD structured data available

### Key Selectors

**Event Listings:**
```css
/* Title container */
h3[data-pw-test-id="event-title"]
h3[data-tracking-id]

/* Title link */
a[data-pw-test-id="event-title-link"]
span[class*="Link"]

/* Event detail bar */
div[data-tracking-id="event-detail-bar"]

/* Location */
div[class*="Location"]
li.Column > div (in detail bar)

/* Date/Time */
span[href*="startDate"]  /* Date with filter link */
div[class*="DateTime"]

/* Price/Cost */
li.Column > div > span  /* In detail section */

/* JSON-LD data */
script[type="application/ld+json"]
```

### Parsing Challenges

1. **Optional Detail Pages** - Some data only on event page
2. **Semantic HTML** - Relies on context, not explicit labels
3. **Date Link Format** - Date wrapped in link with filter
4. **Description Placement** - Can be in multiple locations

### Best Practices

```python
# Use data-testid for reliable selection
title_link = card.find('a', attrs={"data-pw-test-id": "event-title-link"})

# Extract from detail bar section
detail_bar = page_soup.find('div', attrs={"data-tracking-id": "event-detail-bar"})

# Parse JSON-LD for structured data
script = page_soup.find('script', type='application/ld+json')
if script:
    data = json.loads(script.string)
    if data.get('@type') == 'Event':
        # Use structured data for accuracy

# Date extraction from link
span = card.find('span', href=re.compile(r'startDate'))
date_text = span.get_text()  # "Sat, 7 Feb 2026"
parsed_date = parse_date_from_text(date_text)
```

### Deduplication
- **Key:** Event URL (numeric event ID)
- **Method:** Extract ID from URL
- **Storage:** SQLite/Database for persistence

---

## 6. Posh.vip

### Site Structure
- React-based
- Event cards with minimal styling
- Venue-focused information
- VIP/General admission tiers

### Key Selectors

**Event Cards:**
```css
/* Event card container */
div[class*="event-card"]
div[class*="card"]

/* Title/Link */
a[href*="/events/"]
h2, h3

/* Venue/Date */
span[class*="venue"]
div[class*="date"]
span[class*="time"]

/* Price tiers */
div[class*="price"]
span[class*="VIP"]
span[class*="General"]

/* Open bar indicator */
span (contains "open bar")
div (contains "complimentary")
```

### Parsing Challenges

1. **Multiple Price Tiers** - VIP vs General admission
2. **Open Bar Detection** - Need keyword search
3. **Venue Info** - May be primary focus, not event name
4. **Event Link Variation** - Multiple URL formats

### Best Practices

```python
# Detect multiple price tiers
price_elements = card.find_all('div', class_=re.compile(r'price'))
prices = [p.get_text() for p in price_elements]

# Open bar detection - regex search
text = card.get_text()
has_open_bar = bool(re.search(r'open\s+bar|complimentary\s+drinks', text, re.I))

# Parse price from text
price_match = re.search(r'\$(\d+)', text)
if price_match:
    price = int(price_match.group(1)) * 100  # Convert to cents

# Store additional metadata
metadata = {
    'has_open_bar': has_open_bar,
    'price_tiers': ['VIP', 'General'],
    'dress_code': extract_dress_code(text)
}
```

### Deduplication
- **Key:** Event URL + Venue + Date
- **Method:** Combine multiple fields for uniqueness
- **Challenge:** Same venue, recurring events

---

## Data Quality Metrics

### Completeness Scoring

```python
def calculate_completeness(event):
    fields = {
        'title': 1,
        'date': 1,
        'location': 1,
        'link': 1,
        'time': 0.5,
        'description': 0.3,
        'price': 0.3,
        'image': 0.2
    }
    
    score = 0
    max_score = sum(fields.values())
    
    for field, weight in fields.items():
        if event.get(field) and event[field] != 'TBA':
            score += weight
    
    return round(score / max_score * 100, 1)
```

### Expected Completeness Rates

| Source | Title | Date | Location | Time | Link | Avg |
|--------|-------|------|----------|------|------|-----|
| Eventbrite | 100% | 95% | 90% | 85% | 100% | 94% |
| Meetup | 100% | 100% | 100% | 90% | 100% | 98% |
| Luma | 100% | 95% | 80% | 75% | 100% | 90% |
| Dice.fm | 100% | 90% | 85% | 70% | 100% | 89% |
| RA.co | 100% | 85% | 85% | 60% | 100% | 86% |
| Posh.vip | 100% | 90% | 90% | 70% | 100% | 90% |

---

## Deduplication Strategies

### Level 1: Source-Specific ID
```python
# Extract unique ID from each source
source_id = {
    'eventbrite': event['link'].split('/')[-1],
    'meetup': extract_event_id_from_url(event['link']),
    'luma': event['link'].split('/')[-1],
    'dice_fm': event['link'],
    'ra_co': event['link'].split('/')[-1],
    'posh_vip': event['link']
}
```

### Level 2: Normalized Comparison
```python
def normalize_event_key(event):
    """Create normalized key for duplicate detection"""
    return {
        'title': normalize_text(event['title']),
        'location': normalize_text(event['location']),
        'date': event['date'],
        'source': event['source']
    }

def is_duplicate(event1, event2):
    key1 = normalize_event_key(event1)
    key2 = normalize_event_key(event2)
    
    # Same location + date + similar title = duplicate
    return (
        key1['location'] == key2['location'] and
        key1['date'] == key2['date'] and
        similarity(key1['title'], key2['title']) > 0.8
    )
```

### Level 3: Hash-Based Detection
```python
import hashlib

def generate_event_hash(event):
    """Generate hash for fast duplicate detection"""
    key_string = f"{event['title']}|{event['date']}|{event['location']}"
    return hashlib.md5(key_string.encode()).hexdigest()

# Store in set for O(1) lookup
seen_hashes = set()
for event in events:
    event_hash = generate_event_hash(event)
    if event_hash in seen_hashes:
        continue  # Skip duplicate
    seen_hashes.add(event_hash)
```

---

## Recommended Selector Structure

### Universal Pattern (Works for Most Sites)

```python
class EventCardParser:
    """Universal event card parser with fallbacks"""
    
    def extract_title(self, card):
        selectors = [
            ('h3', None),
            ('h2', None),
            ('div[class*="title"]', None),
            ('span[class*="Title"]', None),
            ('img[alt]', 'alt')  # Fallback to image alt
        ]
        
        for selector, attr in selectors:
            elem = card.select_one(selector)
            if elem:
                return elem.get(attr) if attr else elem.get_text(strip=True)
        return None
    
    def extract_date(self, card):
        selectors = [
            ('time[datetime]', 'datetime'),
            ('span[data-date]', 'data-date'),
            ('div[class*="date"]', None),
            # Regex fallback
        ]
        
        for selector, attr in selectors:
            elem = card.select_one(selector)
            if elem:
                value = elem.get(attr) if attr else elem.get_text(strip=True)
                if self.is_valid_date(value):
                    return value
        return None
    
    def extract_link(self, card):
        selectors = [
            ('a[href]', 'href'),
            ('[onclick]', 'onclick'),
        ]
        
        for selector, attr in selectors:
            elem = card.select_one(selector)
            if elem:
                return elem.get(attr)
        return None
```

---

## Testing & Validation

### Selector Testing Script

```python
# Test selector effectiveness
def test_selector(soup, selector, expected_count=None):
    elements = soup.select(selector)
    success = len(elements) > 0
    
    print(f"Selector: {selector}")
    print(f"  Found: {len(elements)} elements")
    print(f"  Success: {'✓' if success else '✗'}")
    
    if elements:
        print(f"  Sample: {str(elements[0])[:100]}")
    
    return success
```

### Validation Checks

```python
# Validate extracted data
def validate_event(event):
    checks = {
        'has_title': bool(event.get('title')),
        'has_date': bool(event.get('date')) and is_valid_date(event['date']),
        'has_link': bool(event.get('link')),
        'has_location': bool(event.get('location')),
        'title_length': len(event.get('title', '')) > 3,
        'date_format': re.match(r'\d{4}-\d{2}-\d{2}', event.get('date', ''))
    }
    
    return {
        'valid': all(checks.values()),
        'checks': checks,
        'score': sum(checks.values()) / len(checks) * 100
    }
```

---

## Maintenance & Updates

### When Selectors Break

1. **Identify** - Which scraper, which field
2. **Inspect** - Open site in browser, inspect HTML
3. **Test** - Create test selector in Python
4. **Update** - Modify selector list with fallbacks
5. **Deploy** - Update scraper code
6. **Monitor** - Check output for issues

### Version Control

```python
# Document selector changes
SELECTOR_VERSIONS = {
    'eventbrite': {
        '2026-02-01': {
            'title': 'h3[data-testid="event-title"]',
            'link': 'a[href*="/events/"]'
        },
        '2026-01-01': {
            'title': 'h3.EventTitle',
            'link': 'a.EventLink'
        }
    }
}
```

---

**Version:** 1.0  
**Last Updated:** 2026-02-05  
**Maintained By:** Development Team
