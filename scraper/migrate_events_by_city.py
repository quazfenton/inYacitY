#!/usr/bin/env python3
"""
Migrate all_events.json to include events_by_city and per-event city.
"""

import json
import os


def migrate(path: str = "all_events.json") -> int:
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return 1

    with open(path, "r") as f:
        data = json.load(f)

    events = data.get("events", [])
    existing_by_city = data.get("events_by_city", {}) or {}
    default_city = data.get("location") or "unknown"

    # Ensure each event has a city.
    for event in events:
        if not event.get("city"):
            event["city"] = default_city

    # Build events_by_city from events (overwrites existing entries for those cities).
    rebuilt = {}
    for event in events:
        city = event.get("city") or default_city
        rebuilt.setdefault(city, []).append(event)

    # Merge with any existing_by_city entries not covered by events list.
    for city, city_events in existing_by_city.items():
        if city not in rebuilt:
            rebuilt[city] = city_events

    data["events_by_city"] = rebuilt
    data["total"] = len(events)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Updated {path} with events_by_city and city fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(migrate())
