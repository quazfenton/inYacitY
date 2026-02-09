#!/usr/bin/env python3
"""
Event Data Patching & Maintenance Script

Handles:
- Patch entries with wrong/missing data
- Sanitize/wash data properly  
- Revisit links to populate empty fields
- Backfill new columns for existing events
- Validate and clean database entries

Usage:
    python patch_events.py --check-missing
    python patch_events.py --sanitize
    python patch_events.py --backfill-field description --source-field title
    python patch_events.py --revisit-links --field description
    python patch_events.py --validate-all
    python patch_events.py --dry-run --check-missing
"""

import asyncio
import json
import os
import sys
import argparse
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import get_config


@dataclass
class PatchResult:
    """Result of a patch operation"""
    success: bool
    patched_count: int
    errors: List[str]
    details: List[Dict]


class EventDataPatcher:
    """Main class for patching and maintaining event data"""
    
    def __init__(self, events_file: str = "all_events.json", dry_run: bool = False):
        self.events_file = events_file
        self.dry_run = dry_run
        self.config = get_config()
        self.data = None
        self.events = []
        self._load_data()
    
    def _load_data(self):
        """Load events from file"""
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    
                # Extract events from nested structure
                self.events = self.data.get('events', [])
                if not self.events and isinstance(self.data, dict) and self.data.get('cities'):
                    for city_id, city_data in self.data['cities'].items():
                        if isinstance(city_data, dict) and 'events' in city_data:
                            self.events.extend(city_data['events'])
                            
                print(f"[OK] Loaded {len(self.events)} events from {self.events_file}")
            except Exception as e:
                print(f"[ERROR] Failed to load events: {e}")
                self.data = {'cities': {}}
                self.events = []
        else:
            print(f"[WARN] Events file not found: {self.events_file}")
            self.data = {'cities': {}}
            self.events = []
    
    def _save_data(self):
        """Save patched data back to file"""
        if self.dry_run:
            print("[DRY-RUN] Would save data (skipped)")
            return
            
        try:
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"[OK] Saved data to {self.events_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save data: {e}")
    
    def _sanitize_text(self, text: str, max_length: int = 1000) -> str:
        """Sanitize text content"""
        if not text:
            return ""
        
        # Remove zero-width characters
        text = re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove control characters except newlines
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length-3] + '...'
        
        return text.strip()
    
    def _validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate and clean URL"""
        if not url:
            return False, ""
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            result = urlparse(url)
            is_valid = all([result.scheme, result.netloc])
            return is_valid, url
        except Exception:
            return False, ""
    
    def _generate_event_hash(self, event: Dict) -> str:
        """Generate consistent hash for event deduplication"""
        key_parts = [
            event.get('title', '').lower().strip(),
            event.get('date', ''),
            event.get('location', '').lower().strip(),
            event.get('city', '').lower().strip(),
            event.get('source', '')
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def check_missing_fields(self, required_fields: List[str] = None) -> PatchResult:
        """Check for events with missing required fields"""
        if required_fields is None:
            required_fields = ['title', 'date', 'location', 'link', 'source']
        
        missing_events = []
        errors = []
        
        for idx, event in enumerate(self.events):
            missing = []
            for field in required_fields:
                if not event.get(field):
                    missing.append(field)
            
            if missing:
                missing_events.append({
                    'index': idx,
                    'event': event,
                    'missing_fields': missing
                })
        
        print(f"\n[CHECK MISSING FIELDS]")
        print(f"Total events checked: {len(self.events)}")
        print(f"Events with missing fields: {len(missing_events)}")
        
        if missing_events:
            print("\nFirst 5 problematic events:")
            for item in missing_events[:5]:
                print(f"  - {item['event'].get('title', 'Untitled')}: missing {', '.join(item['missing_fields'])}")
        
        return PatchResult(
            success=True,
            patched_count=len(missing_events),
            errors=errors,
            details=missing_events
        )
    
    def sanitize_all_events(self) -> PatchResult:
        """Sanitize all text fields in events"""
        patched_count = 0
        errors = []
        details = []
        
        text_fields = ['title', 'description', 'location', 'time']
        
        for idx, event in enumerate(self.events):
            original_event = event.copy()
            modified = False
            
            for field in text_fields:
                if field in event and event[field]:
                    original = event[field]
                    cleaned = self._sanitize_text(original)
                    if original != cleaned:
                        event[field] = cleaned
                        modified = True
            
            # Validate and clean URL
            if 'link' in event:
                is_valid, cleaned_url = self._validate_url(event['link'])
                if not is_valid:
                    errors.append(f"Event {idx}: Invalid URL - {event.get('title', 'Untitled')}")
                elif cleaned_url != event['link']:
                    event['link'] = cleaned_url
                    modified = True
            
            if modified:
                patched_count += 1
                details.append({
                    'index': idx,
                    'title': event.get('title', 'Untitled'),
                    'changes': 'Sanitized text fields'
                })
        
        print(f"\n[SANITIZE EVENTS]")
        print(f"Events sanitized: {patched_count}")
        
        if not self.dry_run and patched_count > 0:
            self._save_data()
        
        return PatchResult(
            success=True,
            patched_count=patched_count,
            errors=errors,
            details=details
        )
    
    def backfill_field(self, target_field: str, source_field: Optional[str] = None, 
                      default_value: Any = None, compute_func=None) -> PatchResult:
        """Backfill a field for all events that have it empty/missing"""
        patched_count = 0
        errors = []
        details = []
        
        print(f"\n[BACKFILL FIELD: {target_field}]")
        
        for idx, event in enumerate(self.events):
            # Skip if field already has value
            if event.get(target_field):
                continue
            
            new_value = None
            
            # Try to compute from source field
            if source_field and source_field in event:
                source_val = event[source_field]
                if compute_func:
                    try:
                        new_value = compute_func(source_val, event)
                    except Exception as e:
                        errors.append(f"Event {idx}: Compute error - {e}")
                else:
                    new_value = source_val
            
            # Use default if still empty
            if new_value is None and default_value is not None:
                new_value = default_value
            
            if new_value is not None:
                event[target_field] = new_value
                patched_count += 1
                details.append({
                    'index': idx,
                    'title': event.get('title', 'Untitled'),
                    'field': target_field,
                    'value': new_value
                })
        
        print(f"Events patched: {patched_count}")
        
        if not self.dry_run and patched_count > 0:
            self._save_data()
        
        return PatchResult(
            success=True,
            patched_count=patched_count,
            errors=errors,
            details=details
        )
    
    def revisit_links(self, target_field: str = 'description', 
                     min_length: int = 10) -> PatchResult:
        """Revisit event links to populate empty fields"""
        patched_count = 0
        errors = []
        details = []
        
        print(f"\n[REVISIT LINKS]")
        print(f"Target field: {target_field}")
        print(f"Min content length: {min_length}")
        
        # Events with empty target field but have links
        to_revisit = []
        for idx, event in enumerate(self.events):
            current_val = event.get(target_field, '')
            link = event.get('link', '')
            
            if (not current_val or len(str(current_val)) < min_length) and link:
                to_revisit.append({'index': idx, 'event': event})
        
        print(f"Events to revisit: {len(to_revisit)}")
        
        if not to_revisit:
            return PatchResult(success=True, patched_count=0, errors=[], details=[])
        
        # Import scraper modules if available
        try:
            # Try to import and use existing scrapers
            print("\nAttempting to scrape missing data...")
            print("(This would use existing scraper logic in production)")
            
            # For now, just mark them for manual review
            for item in to_revisit:
                details.append({
                    'index': item['index'],
                    'title': item['event'].get('title', 'Untitled'),
                    'link': item['event'].get('link', ''),
                    'status': 'needs_scraping'
                })
                
        except Exception as e:
            errors.append(f"Revisit failed: {e}")
        
        return PatchResult(
            success=len(errors) == 0,
            patched_count=patched_count,
            errors=errors,
            details=details
        )
    
    def validate_all_events(self) -> PatchResult:
        """Run comprehensive validation on all events"""
        errors = []
        warnings = []
        valid_count = 0
        
        print(f"\n[VALIDATE ALL EVENTS]")
        
        for idx, event in enumerate(self.events):
            event_errors = []
            
            # Check required fields
            required = ['title', 'date', 'location', 'link', 'source']
            for field in required:
                if not event.get(field):
                    event_errors.append(f"Missing {field}")
            
            # Validate date format
            if event.get('date'):
                try:
                    datetime.strptime(event['date'], '%Y-%m-%d')
                except ValueError:
                    event_errors.append(f"Invalid date format: {event['date']}")
            
            # Validate URL
            if event.get('link'):
                is_valid, _ = self._validate_url(event['link'])
                if not is_valid:
                    event_errors.append("Invalid URL")
            
            # Check for suspicious data
            title = event.get('title', '')
            if len(title) < 3:
                event_errors.append("Title too short")
            if title.isupper():
                warnings.append(f"Event {idx}: Title is all caps")
            
            description = event.get('description', '')
            if description and len(description) < 10:
                warnings.append(f"Event {idx}: Description suspiciously short")
            
            if event_errors:
                errors.append({
                    'index': idx,
                    'title': event.get('title', 'Untitled'),
                    'errors': event_errors
                })
            else:
                valid_count += 1
        
        print(f"Valid events: {valid_count}/{len(self.events)}")
        print(f"Events with errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        
        if errors:
            print("\nFirst 5 errors:")
            for err in errors[:5]:
                print(f"  - {err['title']}: {', '.join(err['errors'])}")
        
        return PatchResult(
            success=len(errors) == 0,
            patched_count=valid_count,
            errors=[f"{e['title']}: {', '.join(e['errors'])}" for e in errors],
            details=errors
        )
    
    def deduplicate_events(self) -> PatchResult:
        """Remove duplicate events based on hash"""
        seen_hashes = {}
        duplicates = []
        unique_events = []
        
        print(f"\n[DEDUPLICATE EVENTS]")
        
        for idx, event in enumerate(self.events):
            event_hash = self._generate_event_hash(event)
            
            if event_hash in seen_hashes:
                duplicates.append({
                    'index': idx,
                    'title': event.get('title', 'Untitled'),
                    'duplicate_of': seen_hashes[event_hash]
                })
            else:
                seen_hashes[event_hash] = idx
                unique_events.append(event)
        
        print(f"Total events: {len(self.events)}")
        print(f"Unique events: {len(unique_events)}")
        print(f"Duplicates found: {len(duplicates)}")
        
        if duplicates and not self.dry_run:
            # Update data structure with unique events only
            if self.data.get('events'):
                self.data['events'] = unique_events
            elif self.data.get('cities'):
                # This is trickier with nested structure - would need to rebuild
                print("[WARN] Nested city structure - manual dedup needed")
            
            self._save_data()
        
        return PatchResult(
            success=True,
            patched_count=len(duplicates),
            errors=[],
            details=duplicates
        )
    
    def generate_report(self, results: List[PatchResult], output_file: str = None):
        """Generate a detailed report of all operations"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'total_events': len(self.events),
            'operations': []
        }
        
        for result in results:
            report['operations'].append({
                'success': result.success,
                'patched_count': result.patched_count,
                'errors': result.errors,
                'details': result.details[:10]  # Limit details
            })
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n[OK] Report saved to {output_file}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description='Event Data Patching & Maintenance Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Check for missing fields
    python patch_events.py --check-missing
    
    # Sanitize all text
    python patch_events.py --sanitize
    
    # Backfill description from title
    python patch_events.py --backfill-field description --source-field title
    
    # Add new column with default value
    python patch_events.py --backfill-field price_tier --default-value 0
    
    # Revisit links to get missing descriptions
    python patch_events.py --revisit-links --field description
    
    # Run all validations
    python patch_events.py --validate-all
    
    # Deduplicate events
    python patch_events.py --deduplicate
    
    # Dry run (don't save changes)
    python patch_events.py --dry-run --sanitize
    
    # Generate report
    python patch_events.py --check-missing --sanitize --report report.json
        """
    )
    
    parser.add_argument('--events-file', default='all_events.json',
                       help='Path to events JSON file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without saving')
    
    # Operations
    parser.add_argument('--check-missing', action='store_true',
                       help='Check for events with missing required fields')
    parser.add_argument('--sanitize', action='store_true',
                       help='Sanitize all text fields')
    parser.add_argument('--backfill-field',
                       help='Backfill a specific field')
    parser.add_argument('--source-field',
                       help='Source field to copy from (use with --backfill-field)')
    parser.add_argument('--default-value',
                       help='Default value for empty fields (use with --backfill-field)')
    parser.add_argument('--revisit-links', action='store_true',
                       help='Revisit links to populate empty fields')
    parser.add_argument('--field', default='description',
                       help='Target field for revisit/backfill')
    parser.add_argument('--validate-all', action='store_true',
                       help='Run comprehensive validation')
    parser.add_argument('--deduplicate', action='store_true',
                       help='Remove duplicate events')
    
    # Output
    parser.add_argument('--report',
                       help='Generate JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize patcher
    patcher = EventDataPatcher(
        events_file=args.events_file,
        dry_run=args.dry_run
    )
    
    results = []
    
    # Execute requested operations
    if args.check_missing:
        result = patcher.check_missing_fields()
        results.append(result)
    
    if args.sanitize:
        result = patcher.sanitize_all_events()
        results.append(result)
    
    if args.backfill_field:
        # Parse default value
        default_value = args.default_value
        if default_value is not None:
            # Try to convert to int if it looks like a number
            try:
                default_value = int(default_value)
            except ValueError:
                pass
        
        result = patcher.backfill_field(
            target_field=args.backfill_field,
            source_field=args.source_field,
            default_value=default_value
        )
        results.append(result)
    
    if args.revisit_links:
        result = patcher.revisit_links(target_field=args.field)
        results.append(result)
    
    if args.validate_all:
        result = patcher.validate_all_events()
        results.append(result)
    
    if args.deduplicate:
        result = patcher.deduplicate_events()
        results.append(result)
    
    # If no operation specified, show help
    if not any([args.check_missing, args.sanitize, args.backfill_field,
                args.revisit_links, args.validate_all, args.deduplicate]):
        parser.print_help()
        return
    
    # Generate report if requested
    if args.report:
        patcher.generate_report(results, args.report)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    total_patched = sum(r.patched_count for r in results)
    total_errors = sum(len(r.errors) for r in results)
    print(f"Operations completed: {len(results)}")
    print(f"Total items patched: {total_patched}")
    print(f"Total errors: {total_errors}")
    if args.dry_run:
        print("\n[DRY-RUN] No changes were saved")
    print("="*70)


if __name__ == "__main__":
    main()
