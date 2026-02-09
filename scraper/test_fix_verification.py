#!/usr/bin/env python3
"""
Test script to verify that the date parsing issue is fixed
"""

from db_sync_enhanced import EventDataValidator

def test_original_problematic_events():
    """Test the events that were originally failing"""
    problematic_events = [
        {
            'title': 'Homicide: Life on the Streets (DJs)',
            'date': 'Mon, Feb 9',
            'location': 'Venue A',
            'link': 'https://example.com/event1',
            'source': 'test_source'
        },
        {
            'title': 'CLOSED Tonight',
            'date': 'Mon, Feb 9',
            'location': 'Venue B',
            'link': 'https://example.com/event2',
            'source': 'test_source'
        },
        {
            'title': 'Christina Galisatus, Nick Dorian',
            'date': 'Mon, Feb 9',
            'location': 'Venue C',
            'link': 'https://example.com/event3',
            'source': 'test_source'
        },
        {
            'title': 'Nightshift Afterhours',
            'date': 'Mon, Feb 9',
            'location': 'Venue D',
            'link': 'https://example.com/event4',
            'source': 'test_source'
        },
        {
            'title': 'Thrash n Trash- Punk Rock Flea Market',
            'date': 'Sat, Feb 7',
            'location': 'Venue E',
            'link': 'https://example.com/event5',
            'source': 'test_source'
        }
    ]

    print("Testing originally problematic events...")
    all_valid = True
    for i, event in enumerate(problematic_events, 1):
        is_valid, cleaned, errors = EventDataValidator.validate_event(event)
        print(f"\nEvent {i}: {event['title']}")
        print(f"  Date: {event['date']} -> {cleaned.get('date', 'N/A') if is_valid else 'FAILED'}")
        print(f"  Valid: {is_valid}")
        if not is_valid:
            print(f"  Errors: {errors}")
            all_valid = False
    
    print(f"\nAll events valid: {all_valid}")
    if all_valid:
        print("✅ SUCCESS: All originally problematic events now pass validation!")
    else:
        print("❌ FAILURE: Some events still fail validation")
    
    return all_valid

if __name__ == "__main__":
    test_original_problematic_events()