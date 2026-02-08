#!/usr/bin/env python3
"""Test script to debug the date parsing function"""

from db_sync_enhanced import EventDataValidator
from datetime import datetime

# Test the date parsing function
test_dates = ['Mon, Feb 9', 'Sat, Feb 7', '2026-02-09', '02/09/2026', 'Feb 9, 2026']

print("Testing date parsing function:")
for date_str in test_dates:
    result = EventDataValidator.parse_flexible_date(date_str)
    print(f"'{date_str}' -> '{result}'")

# Also test the validation function
print("\nTesting validation function:")
test_event = {
    'title': 'Test Event',
    'date': 'Mon, Feb 9',
    'location': 'Test Location',
    'link': 'https://example.com',
    'source': 'test'
}

is_valid, cleaned, errors = EventDataValidator.validate_event(test_event)
print(f"Valid: {is_valid}")
print(f"Cleaned: {cleaned}")
print(f"Errors: {errors}")