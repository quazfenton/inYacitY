#!/usr/bin/env python3
"""
AgentBrowser2 - Robust event scraping using agent-browser CLI
Enhanced with semantic extraction and adaptive parsing
"""

import asyncio
import json
import os
import re
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

class AgentBrowser2:
    """
    Enhanced wrapper for agent-browser CLI with semantic search and reliable extraction
    """
    def __init__(self, session_name: Optional[str] = None, headless: bool = True):
        self.session_name = session_name or f"session_{int(time.time())}"
        self.headless = headless
        self.last_output = ""
        self.is_closed = False

    def _run_cmd(self, cmd_args: List[str], timeout: int = 120) -> Tuple[str, bool]:
        """Run agent-browser command with enhanced error handling"""
        base_cmd = ["agent-browser"]
        if self.session_name:
            base_cmd.extend(["--session", self.session_name])
        
        if self.headless:
            # Note: agent-browser is headed by default, so we might need to handle this
            pass
        
        full_cmd = base_cmd + cmd_args
        
        try:
            # print(f"Executing: {' '.join(full_cmd)}")
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            self.last_output = result.stdout
            
            if result.returncode != 0:
                # If it failed because session doesn't exist, that's often okay for first command
                if "Session not found" in result.stderr and cmd_args[0] == "open":
                    pass 
                else:
                    print(f"Error ({result.returncode}): {result.stderr}")
                    return result.stderr, False
            return result.stdout, True
        except subprocess.TimeoutExpired:
            print(f"Command timed out: {' '.join(full_cmd)}")
            return "Timeout", False
        except Exception as e:
            print(f"Exception running command: {e}")
            return str(e), False

    async def navigate(self, url: str) -> bool:
        """Open a URL and wait for load"""
        print(f"Navigating to: {url}")
        _, success = self._run_cmd(["open", url])
        if success:
            await asyncio.sleep(5) # Give it time to settle
        return success

    async def get_page_info(self) -> Dict[str, str]:
        """Get basic page metadata"""
        title, _ = self._run_cmd(["get", "title"])
        url, _ = self._run_cmd(["get", "url"])
        return {"title": title.strip(), "url": url.strip()}

    async def semantic_extract_events(self) -> List[Dict]:
        """
        Extract events using semantic analysis of the snapshot
        """
        print("Performing semantic extraction...")
        snapshot, success = self._run_cmd(["snapshot"])
        if not success:
            return []
            
        events = []
        
        # Look for patterns that indicate event listings
        # Common pattern: [ref=XX] Title ... Date ... Location
        lines = snapshot.split('\n')
        
        current_event = None
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Check if this line looks like a new event entry
            # Usually starts with a reference or a bold title
            ref_match = re.search(r'\[ref=(\d+)\]', line)
            
            if ref_match:
                # If we were already building an event, save it
                if current_event and current_event.get('title'):
                    events.append(current_event)
                
                ref_id = ref_match.group(1)
                # Clean up the line to get the title
                title_part = re.sub(r'\[ref=\d+\]', '', line).strip()
                title_part = re.sub(r'\[.*?\]', '', title_part).strip() # Remove other refs
                
                current_event = {
                    'ref': ref_id,
                    'title': title_part,
                    'date': None,
                    'location': None,
                    'link': None,
                    'source_text': line
                }
            elif current_event:
                # Try to extract more info for the current event from subsequent lines
                # Look for dates (e.g., "Feb 20", "2024-02-20", "Saturday")
                date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2}|(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*|202\d-\d{2}-\d{2})', line)
                if date_match and not current_event['date']:
                    current_event['date'] = date_match.group(1)
                
                # Look for locations (often after a pipe or on a new line with venue indicators)
                if ("@" in line or "at " in line.lower() or "Venue" in line) and not current_event['location']:
                    current_event['location'] = line.strip("@ ").strip()

        # Add the last one
        if current_event and current_event.get('title'):
            events.append(current_event)
            
        print(f"Semantically found {len(events)} potential events")
        return events

    async def robust_scrape(self, url: str, target_source: str) -> List[Dict]:
        """
        Perform a robust scrape of a target URL
        """
        if not await self.navigate(url):
            return []
            
        # Handle common blockers
        snapshot, _ = self._run_cmd(["snapshot"])
        if "Accept" in snapshot or "Cookie" in snapshot or "Consent" in snapshot:
            print("Detected consent banner, attempting to clear...")
            self._run_cmd(["find", "role", "button", "click", "--name", "Accept"])
            await asyncio.sleep(2)

        # Scroll to load more content
        print("Scrolling to load dynamic content...")
        self._run_cmd(["scroll", "down", "1000"])
        await asyncio.sleep(2)
        
        # Extract
        events = await self.semantic_extract_events()
        
        # Clean and standardize
        final_events = []
        for e in events:
            # Skip noise
            if len(e['title']) < 5 or any(term in e['title'].lower() for term in ["login", "sign up", "menu", "search"]):
                continue
                
            final_events.append({
                'title': e['title'],
                'date': e.get('date', 'TBA'),
                'location': e.get('location', 'Location TBA'),
                'link': url, # Default to source URL if specific link not found
                'source': target_source
            })
            
        return final_events

    async def close(self):
        if not self.is_closed:
            self._run_cmd(["close"])
            self.is_closed = True

async def main():
    agent = AgentBrowser2(session_name="test_session")
    try:
        # Example: Scrape RA.co with AgentBrowser
        events = await agent.robust_scrape("https://ra.co/events/us/newyorkcity", "RA.co")
        print(f"\nScraped {len(events)} events:")
        for e in events[:5]:
            print(f"  - {e['title']} | {e['date']} | {e['location']}")
            
        if not events:
            print("No events found. Check if blocked or if selectors changed.")
            
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
