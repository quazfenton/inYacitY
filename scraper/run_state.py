#!/usr/bin/env python3
"""
Run State Persistence - Tracks scraper progress so crashed runs can resume.

Writes state after each scraper completes. On next run, reads state and
skips already-completed scrapers, resuming from the failure point.

State file: scraper/run_state.json
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

STATE_FILE = Path(__file__).parent / "run_state.json"

SCRAPER_ORDER = [
    "eventbrite",
    "meetup",
    "luma",
    "dice_fm",
    "ra_co",
    "discovery",
    "proxy_fallback",
]


def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"run_id": None, "location": None, "completed": {}, "events_found": {}, "started_at": None}


def _save_state(state: Dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def start_run(location: str, force_fresh: bool = False) -> Dict:
    """Start a new run or resume from existing state."""
    state = _load_state()

    if force_fresh or state.get("location") != location or state.get("completed") is None:
        state = {
            "run_id": datetime.now().isoformat(),
            "location": location,
            "completed": {},
            "events_found": {},
            "started_at": datetime.now().isoformat(),
        }
        _save_state(state)
        print(f"[State] New run started: {state['run_id']}")
        return state

    print(f"[State] Resuming run from {state.get('started_at', 'unknown')}")
    completed = state.get("completed", {})
    print(f"[State] Already completed: {list(completed.keys())}")
    return state


def mark_scraper_complete(scraper_name: str, event_count: int):
    """Mark a scraper as completed with its event count."""
    state = _load_state()
    state["completed"][scraper_name] = datetime.now().isoformat()
    state["events_found"][scraper_name] = event_count
    _save_state(state)
    print(f"[State] Marked {scraper_name} complete ({event_count} events)")


def is_scraper_complete(scraper_name: str) -> bool:
    """Check if a scraper already completed in current run."""
    state = _load_state()
    return scraper_name in state.get("completed", {})


def get_completed_scrapers() -> Dict[str, str]:
    """Get dict of completed scrapers with their timestamps."""
    state = _load_state()
    return state.get("completed", {})


def get_next_scraper() -> Optional[str]:
    """Get the next scraper that hasn't completed yet."""
    state = _load_state()
    completed = state.get("completed", {})
    for scraper in SCRAPER_ORDER:
        if scraper not in completed:
            return scraper
    return None


def clear_state():
    """Clear run state (call at end of successful full run)."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def get_events_found() -> Dict[str, int]:
    """Get event counts per completed scraper."""
    state = _load_state()
    return state.get("events_found", {})


def load_resumed_events(location: str, all_events_path: str) -> List[Dict]:
    """
    When resuming from crash, load previously saved events from all_events.json.
    This ensures events from completed scrapers before the crash are not lost.
    """
    if not os.path.exists(all_events_path):
        return []
    try:
        with open(all_events_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("cities"):
            city_data = data["cities"].get(location, {})
            events = city_data.get("events", [])
            print(f"[State] Loaded {len(events)} previously saved events for {location}")
            return events
    except (json.JSONDecodeError, IOError) as e:
        print(f"[State] Warning: Could not load previous events: {e}")
    return []
