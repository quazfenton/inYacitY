# New Event Source Implementation Guide
**For:** Nocturne (inyAcity)  
**Date:** February 5, 2026  
**Status:** Ready for implementation

---

## 1. DICE.FM Scraper Implementation

### Overview
Dice.fm has a GraphQL API that can be accessed with minimal authentication for public event discovery.

### API Endpoint
```
https://partners-endpoint.dice.fm/graphql
```

### Implementation

Create file: `scraper/dice_fm.py`

```python
#!/usr/bin/env python3
"""
Dice.fm scraper - Uses GraphQL API for underground electronic music events
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp


DICE_API_URL = "https://partners-endpoint.dice.fm/graphql"

# City mapping for Dice.fm
CITY_TO_DICE_MARKET = {
    "ca--los-angeles": "los-angeles",
    "ny--new-york": "new-york",
    "ca--san-francisco": "san-francisco",
    "wa--seattle": "seattle",
    "il--chicago": "chicago",
    "tx--austin": "austin",
    "fl--miami": "miami",
    "co--denver": "denver",
    "ma--boston": "boston",
    "ga--atlanta": "atlanta",
    "or--portland": "portland",
    "nv--las-vegas": "las-vegas",
    "dc--washington": "washington-dc",
}


async def fetch_dice_events(city: str, limit: int = 50) -> List[Dict]:
    """
    Fetch events from Dice.fm GraphQL API
    
    Args:
        city: City code (e.g., "ca--los-angeles")
        limit: Max events to fetch
    
    Returns:
        List of normalized event dictionaries
    """
    
    dice_market = CITY_TO_DICE_MARKET.get(city)
    if not dice_market:
        print(f"City {city} not supported by Dice.fm")
        return []
    
    # GraphQL query for events
    query = """
    query GetEvents($market: String!, $limit: Int!) {
      viewer {
        events(
          first: $limit,
          where: {
            market: { eq: $market },
            state: { eq: ON_SALE }
          }
        ) {
          edges {
            node {
              id
              name
              startDatetime
              endDatetime
              description
              url
              images {
                type
                url
              }
              venues {
                name
                address {
                  street
                  city
                  state
                  zip
                }
              }
              artists {
                name
              }
              genres
              ticketTypes {
                name
                price
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "market": dice_market,
        "limit": limit
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                # Dice.fm may require auth token for some endpoints
                # Try without first, add if needed
            }
            
            payload = {
                "query": query,
                "variables": variables
            }
            
            async with session.post(
                DICE_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    print(f"Dice.fm API error: {response.status}")
                    return []
                
                data = await response.json()
                
                if "errors" in data:
                    print(f"GraphQL errors: {data['errors']}")
                    return []
                
                events = []
                edges = data.get("data", {}).get("viewer", {}).get("events", {}).get("edges", [])
                
                for edge in edges:
                    node = edge.get("node", {})
                    if not node:
                        continue
                    
                    # Parse dates
                    start_dt = node.get("startDatetime", "")
                    event_date = datetime.fromisoformat(start_dt.replace("Z", "+00:00")).date() if start_dt else None
                    event_time = datetime.fromisoformat(start_dt.replace("Z", "+00:00")).strftime("%I:%M %p") if start_dt else "TBA"
                    
                    # Get venue info
                    venues = node.get("venues", [])
                    venue = venues[0] if venues else {}
                    venue_name = venue.get("name", "Location TBA")
                    address = venue.get("address", {})
                    location_parts = [venue_name]
                    if address.get("city"):
                        location_parts.append(f"{address.get('city')}, {address.get('state', '')}")
                    location = " · ".join(location_parts)
                    
                    # Get artists
                    artists = [a.get("name") for a in node.get("artists", []) if a.get("name")]
                    artist_str = f" feat. {', '.join(artists)}" if artists else ""
                    
                    # Build description
                    description = node.get("description", "")
                    if artists:
                        description = f"Lineup: {', '.join(artists)}. {description}"
                    
                    event = {
                        "title": f"{node.get('name', 'Untitled Event')}{artist_str}",
                        "link": node.get("url", ""),
                        "date": event_date,
                        "time": event_time,
                        "location": location,
                        "description": description[:300] + "..." if len(description) > 300 else description,
                        "source": "dice.fm",
                        "genres": node.get("genres", []),
                        "image": next((img.get("url") for img in node.get("images", []) if img.get("type") == "BANNER"), None)
                    }
                    events.append(event)
                
                return events
                
    except Exception as e:
        print(f"Error fetching Dice.fm events: {e}")
        return []


async def scrape_dice_fm(city: str, output_file: str = "dice_events.json"):
    """
    Main entry point for Dice.fm scraping
    """
    print(f"Scraping Dice.fm for {city}...")
    events = await fetch_dice_events(city)
    
    # Load existing to avoid duplicates
    existing_links = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                existing_links = {e.get("link") for e in data.get("events", [])}
        except:
            pass
    
    # Filter duplicates
    new_events = [e for e in events if e.get("link") not in existing_links]
    
    # Save
    with open(output_file, 'w') as f:
        json.dump({"events": events, "count": len(events)}, f, indent=2, default=str)
    
    print(f"Saved {len(new_events)} new events from Dice.fm")
    return new_events


if __name__ == "__main__":
    # Test
    asyncio.run(scrape_dice_fm("ny--new-york"))
```

### Configuration Update

Add to `scraper/config.json`:
```json
{
  "SOURCES": {
    "ENABLE_DICE_FM": true,
    "DICE_FM_MARKETS": {
      "ca--los-angeles": "los-angeles",
      "ny--new-york": "new-york",
      "ca--san-francisco": "san-francisco"
    }
  }
}
```

---

## 2. RESIDENT ADVISOR (RA.co) Scraper Implementation

### Overview
RA requires browser-based scraping due to anti-bot measures. We'll use Playwright similar to the existing scrapers.

### Implementation

Create file: `scraper/resident_advisor.py`

```python
#!/usr/bin/env python3
"""
Resident Advisor (RA.co) scraper for underground electronic music events
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


# City mapping for RA
CITY_TO_RA_URL = {
    "ca--los-angeles": "https://ra.co/events/us/los-angeles",
    "ny--new-york": "https://ra.co/events/us/new-york",
    "ca--san-francisco": "https://ra.co/events/us/san-francisco",
    "wa--seattle": "https://ra.co/events/us/seattle",
    "il--chicago": "https://ra.co/events/us/chicago",
    "tx--austin": "https://ra.co/events/us/austin",
    "fl--miami": "https://ra.co/events/us/miami",
    "co--denver": "https://ra.co/events/us/denver",
    "ma--boston": "https://ra.co/events/us/boston",
    "ga--atlanta": "https://ra.co/events/us/atlanta",
    "or--portland": "https://ra.co/events/us/portland",
    "dc--washington": "https://ra.co/events/us/washington",
}


async def scrape_ra_events(city: str, max_events: int = 50) -> List[Dict]:
    """
    Scrape events from Resident Advisor
    
    Args:
        city: City code (e.g., "ny--new-york")
        max_events: Maximum events to scrape
    
    Returns:
        List of normalized event dictionaries
    """
    
    ra_url = CITY_TO_RA_URL.get(city)
    if not ra_url:
        print(f"City {city} not mapped for Resident Advisor")
        return []
    
    events = []
    
    # Import from consent_handler (reuse existing infrastructure)
    from consent_handler import (
        create_undetected_browser,
        close_undetected_browser,
        navigate_with_cloudflare_bypass,
    )
    
    browser = None
    browser_type = None
    
    try:
        browser, page, browser_type = await create_undetected_browser(
            use_pydoll=True,
            use_patchright=True,
            headless=True
        )
        
        print(f"Scraping Resident Advisor: {ra_url}")
        
        nav_success = await navigate_with_cloudflare_bypass(page, ra_url, browser_type, timeout=30000)
        if not nav_success:
            print("Failed to navigate to RA")
            return []
        
        # Wait for events to load
        await page.wait_for_selector("[data-testid='event-list']", timeout=10000)
        
        # Scroll to load more events
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
        
        # Get content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find event cards
        event_cards = soup.find_all("div", attrs={"data-testid": "event-card"})
        
        for card in event_cards[:max_events]:
            try:
                # Extract event details
                title_elem = card.find("h3") or card.find("h2")
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Event"
                
                # Get event link
                link_elem = card.find("a", href=re.compile(r"/events/\d+"))
                event_url = f"https://ra.co{link_elem['href']}" if link_elem else ""
                
                # Get date/time
                date_elem = card.find("time")
                date_str = date_elem.get("datetime") if date_elem else ""
                event_date = None
                event_time = "TBA"
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        event_date = dt.date()
                        event_time = dt.strftime("%I:%M %p")
                    except:
                        pass
                
                # Get venue
                venue_elem = card.find("a", href=re.compile(r"/clubs/|/venues/"))
                venue = venue_elem.get_text(strip=True) if venue_elem else "Location TBA"
                
                # Get lineup/artists
                artist_elems = card.find_all("a", href=re.compile(r"/dj/|/artists/"))
                artists = [a.get_text(strip=True) for a in artist_elems if a.get_text(strip=True)]
                
                # Get image
                img_elem = card.find("img")
                image_url = img_elem.get("src") if img_elem else None
                
                # Build description
                description = ""
                if artists:
                    description = f"Lineup: {', '.join(artists[:5])}"
                
                event = {
                    "title": title,
                    "link": event_url,
                    "date": event_date,
                    "time": event_time,
                    "location": venue,
                    "description": description,
                    "source": "resident-advisor",
                    "genres": ["electronic"],  # RA is electronic-focused
                    "image": image_url,
                    "artists": artists
                }
                events.append(event)
                
            except Exception as e:
                print(f"Error parsing RA event card: {e}")
                continue
        
    except Exception as e:
        print(f"Error scraping Resident Advisor: {e}")
    
    finally:
        if browser:
            await close_undetected_browser(browser, browser_type)
    
    return events


async def scrape_resident_advisor(city: str, output_file: str = "ra_events.json"):
    """
    Main entry point for RA scraping
    """
    print(f"Scraping Resident Advisor for {city}...")
    events = await scrape_ra_events(city)
    
    # Deduplication against existing
    existing_links = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                existing_links = {e.get("link") for e in data.get("events", [])}
        except:
            pass
    
    new_events = [e for e in events if e.get("link") not in existing_links]
    
    with open(output_file, 'w') as f:
        json.dump({"events": events, "count": len(events)}, f, indent=2, default=str)
    
    print(f"Saved {len(new_events)} new events from Resident Advisor")
    return new_events


if __name__ == "__main__":
    asyncio.run(scrape_resident_advisor("ny--new-york"))
```

---

## 3. SONGKICK Implementation

Create file: `scraper/songkick.py`

```python
#!/usr/bin/env python3
"""
Songkick API scraper for live music events
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict
import aiohttp


SONGKICK_API_KEY = os.environ.get("SONGKICK_API_KEY", "")
SONGKICK_BASE_URL = "https://api.songkick.com/api/3.0"

# Metro area IDs for Songkick
CITY_TO_METRO_ID = {
    "ca--los-angeles": "17835",
    "ny--new-york": "7644",
    "ca--san-francisco": "26330",
    "wa--seattle": "2846",
    "il--chicago": "9426",
    "tx--austin": "9179",
    "fl--miami": "9776",
    "co--denver": "6404",
    "ma--boston": "18842",
    "ga--atlanta": "4120",
    "or--portland": "12283",
    "dc--washington": "1409",
}


async def fetch_songkick_events(city: str) -> List[Dict]:
    """
    Fetch events from Songkick API
    """
    if not SONGKICK_API_KEY:
        print("SONGKICK_API_KEY not set")
        return []
    
    metro_id = CITY_TO_METRO_ID.get(city)
    if not metro_id:
        print(f"City {city} not mapped for Songkick")
        return []
    
    url = f"{SONGKICK_BASE_URL}/metro_areas/{metro_id}/calendar.json"
    params = {
        "apikey": SONGKICK_API_KEY,
        "per_page": 50
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    print(f"Songkick API error: {response.status}")
                    return []
                
                data = await response.json()
                events = []
                
                results = data.get("resultsPage", {}).get("results", {}).get("event", [])
                
                for event in results:
                    # Parse date/time
                    start = event.get("start", {})
                    date_str = start.get("date", "")
                    time_str = start.get("time", "")
                    
                    event_date = None
                    event_time = "TBA"
                    
                    if date_str:
                        try:
                            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except:
                            pass
                    
                    if time_str:
                        try:
                            dt = datetime.strptime(time_str, "%H:%M:%S")
                            event_time = dt.strftime("%I:%M %p")
                        except:
                            pass
                    
                    # Get venue
                    venue = event.get("venue", {})
                    venue_name = venue.get("displayName", "Location TBA")
                    
                    # Get artists
                    performances = event.get("performance", [])
                    artists = [p.get("artist", {}).get("displayName") for p in performances if p.get("artist")]
                    
                    # Build title
                    title = event.get("displayName", "Unknown Event")
                    
                    events.append({
                        "title": title,
                        "link": event.get("uri", ""),
                        "date": event_date,
                        "time": event_time,
                        "location": venue_name,
                        "description": f"Performances: {', '.join(artists[:5])}" if artists else "",
                        "source": "songkick",
                        "artists": artists
                    })
                
                return events
                
    except Exception as e:
        print(f"Error fetching Songkick events: {e}")
        return []


async def scrape_songkick(city: str, output_file: str = "songkick_events.json"):
    """
    Main entry point for Songkick scraping
    """
    print(f"Scraping Songkick for {city}...")
    events = await fetch_songkick_events(city)
    
    with open(output_file, 'w') as f:
        json.dump({"events": events, "count": len(events)}, f, indent=2, default=str)
    
    print(f"Saved {len(events)} events from Songkick")
    return events


if __name__ == "__main__":
    asyncio.run(scrape_songkick("ny--new-york"))
```

---

## 4. Integration with Existing Scraper Pipeline

Update `scraper/run.py` to include new sources:

```python
# In run.py, add to imports
from dice_fm import scrape_dice_fm
from resident_advisor import scrape_resident_advisor
from songkick import scrape_songkick

# In run_all_scrapers():
async def run_all_scrapers():
    config = load_config()
    city = config.get("LOCATION", "ca--los-angeles")
    
    all_events = []
    
    # Existing scrapers
    if config.get("MODES", {}).get("ENABLE_EVENTBRITE_SCRAPING", True):
        events = await scrape_eventbrite(city)
        all_events.extend(events)
    
    if config.get("MODES", {}).get("ENABLE_MEETUP_SCRAPING", True):
        events = await scrape_meetup(city)
        all_events.extend(events)
    
    if config.get("MODES", {}).get("ENABLE_LUMA_SCRAPING", True):
        events = await scrape_luma(city)
        all_events.extend(events)
    
    # NEW: Add these scrapers
    if config.get("SOURCES", {}).get("ENABLE_DICE_FM", True):
        events = await scrape_dice_fm(city)
        all_events.extend(events)
    
    if config.get("SOURCES", {}).get("ENABLE_RESIDENT_ADVISOR", True):
        events = await scrape_resident_advisor(city)
        all_events.extend(events)
    
    if config.get("SOURCES", {}).get("ENABLE_SONGKICK", True):
        events = await scrape_songkick(city)
        all_events.extend(events)
    
    # Merge and deduplicate
    # ... rest of existing logic
```

---

## 5. Database Schema Updates

Add new fields to track enriched data:

```python
# In backend/database.py, update Event model:

class Event(Base):
    __tablename__ = "events"
    
    # Existing fields...
    
    # NEW FIELDS for enriched data
    genres = Column(JSON, nullable=True)  # ["techno", "house"]
    artists = Column(JSON, nullable=True)  # ["Artist 1", "Artist 2"]
    image_url = Column(String(1000), nullable=True)
    vibe_score = Column(Integer, nullable=True)  # 1-10
    crowd_type = Column(String(50), nullable=True)  # "industry", "students"
    ticket_price_min = Column(Float, nullable=True)
    ticket_price_max = Column(Float, nullable=True)
    is_sold_out = Column(Boolean, default=False)
    
    # For AI enrichment
    ai_tags = Column(JSON, nullable=True)  # AI-generated tags
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
```

---

## 6. Environment Variables

Add to `.env.example`:

```bash
# New API Keys
SONGKICK_API_KEY=your_songkick_api_key_here

# Dice.fm (if auth required)
DICE_FM_API_KEY=optional

# OpenAI (for AI enrichment)
OPENAI_API_KEY=your_openai_key_here
```

---

## 7. Testing Checklist

- [ ] Test Dice.fm scraper for each mapped city
- [ ] Test Resident Advisor scraper (check anti-bot detection)
- [ ] Test Songkick API with valid key
- [ ] Verify deduplication works across all sources
- [ ] Test database migration with new fields
- [ ] Verify frontend displays new event data correctly
- [ ] Test email digest includes events from all sources

---

## 8. Deployment Steps

1. **Add environment variables** to production
2. **Run database migration** for new fields
3. **Deploy new scraper code**
4. **Update cron schedule** if needed (more sources = longer scraping time)
5. **Monitor logs** for any new scraping failures

---

*Implementation ready. Estimated time: 1-2 weeks for all three sources.*
