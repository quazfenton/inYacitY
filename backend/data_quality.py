#!/usr/bin/env python3
"""
Data quality monitoring and duplicate detection
Ensures high-quality event data and detects duplicates across sources
"""

import asyncio
import hashlib
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class DataQualityReport:
    """Report of data quality issues"""
    total_events: int
    missing_fields: Dict[str, int]
    duplicates_found: int
    suspicious_events: List[Dict]
    quality_score: float  # 0-100


class DataQualityChecker:
    """Checks and reports on data quality issues"""
    
    def __init__(self):
        self.quality_rules = {
            'title': {
                'min_length': 5,
                'max_length': 200,
                'required': True
            },
            'description': {
                'min_length': 20,
                'max_length': 5000,
                'required': False
            },
            'location': {
                'min_length': 3,
                'required': True
            },
            'date': {
                'required': True,
                'not_past': True
            },
            'link': {
                'required': True,
                'valid_url': True
            }
        }
    
    def check_event_quality(self, event: Dict) -> Tuple[bool, List[str]]:
        """
        Check quality of a single event
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        for field, rules in self.quality_rules.items():
            value = event.get(field)
            
            # Check required fields
            if rules.get('required') and not value:
                issues.append(f"Missing required field: {field}")
                continue
            
            if not value:
                continue
            
            # Check length
            if 'min_length' in rules and len(str(value)) < rules['min_length']:
                issues.append(f"{field} too short (min {rules['min_length']} chars)")
            
            if 'max_length' in rules and len(str(value)) > rules['max_length']:
                issues.append(f"{field} too long (max {rules['max_length']} chars)")
            
            # Check date not in past
            if field == 'date' and rules.get('not_past'):
                try:
                    event_date = value if isinstance(value, date) else datetime.strptime(str(value), '%Y-%m-%d').date()
                    if event_date < date.today():
                        issues.append(f"Event date is in the past: {event_date}")
                except:
                    issues.append(f"Invalid date format: {value}")
            
            # Check URL validity
            if field == 'link' and rules.get('valid_url'):
                if not value.startswith(('http://', 'https://')):
                    issues.append(f"Invalid URL format: {value}")
        
        return len(issues) == 0, issues
    
    async def analyze_events(self, events: List[Dict]) -> DataQualityReport:
        """
        Analyze list of events and generate quality report
        
        Args:
            events: List of event dictionaries
        
        Returns:
            DataQualityReport with findings
        """
        missing_fields = {
            'title': 0,
            'description': 0,
            'location': 0,
            'date': 0,
            'link': 0
        }
        
        suspicious = []
        valid_count = 0
        
        for event in events:
            is_valid, issues = self.check_event_quality(event)
            
            if is_valid:
                valid_count += 1
            else:
                suspicious.append({
                    'event': event,
                    'issues': issues
                })
            
            # Count missing fields
            for field in missing_fields.keys():
                if not event.get(field):
                    missing_fields[field] += 1
        
        # Calculate quality score
        quality_score = (valid_count / len(events) * 100) if events else 0
        
        return DataQualityReport(
            total_events=len(events),
            missing_fields=missing_fields,
            duplicates_found=0,  # Will be set by duplicate detector
            suspicious_events=suspicious,
            quality_score=round(quality_score, 2)
        )


class DuplicateDetector:
    """Detects duplicate events using multiple strategies"""
    
    def __init__(
        self,
        title_similarity_threshold: float = 0.85,
        location_similarity_threshold: float = 0.70,
        time_window_hours: int = 2
    ):
        self.title_threshold = title_similarity_threshold
        self.location_threshold = location_similarity_threshold
        self.time_window = timedelta(hours=time_window_hours)
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison"""
        return ' '.join(str(text).lower().split())
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _generate_event_hash(self, event: Dict) -> str:
        """
        Generate deterministic hash for event
        Used for exact duplicate detection
        """
        # Create normalized key
        title = self._normalize_string(event.get('title', ''))
        location = self._normalize_string(event.get('location', ''))
        event_date = str(event.get('date', ''))
        
        key = f"{title}|{location}|{event_date}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def find_exact_duplicates(self, events: List[Dict]) -> List[Tuple[int, int]]:
        """
        Find exact duplicates using hash comparison
        
        Returns:
            List of (index1, index2) tuples for duplicates
        """
        seen_hashes = {}
        duplicates = []
        
        for idx, event in enumerate(events):
            event_hash = self._generate_event_hash(event)
            
            if event_hash in seen_hashes:
                duplicates.append((seen_hashes[event_hash], idx))
            else:
                seen_hashes[event_hash] = idx
        
        return duplicates
    
    def find_fuzzy_duplicates(self, events: List[Dict]) -> List[Dict]:
        """
        Find potential duplicates using fuzzy matching
        
        Returns:
            List of duplicate groups with confidence scores
        """
        duplicates = []
        checked_pairs = set()
        
        for i, event1 in enumerate(events):
            for j, event2 in enumerate(events[i+1:], start=i+1):
                # Skip if already checked
                pair_key = tuple(sorted([i, j]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                # Check date proximity
                date1 = event1.get('date')
                date2 = event2.get('date')
                
                if date1 != date2:
                    continue
                
                # Compare titles
                title1 = self._normalize_string(event1.get('title', ''))
                title2 = self._normalize_string(event2.get('title', ''))
                title_sim = self._calculate_similarity(title1, title2)
                
                # Compare locations
                loc1 = self._normalize_string(event1.get('location', ''))
                loc2 = self._normalize_string(event2.get('location', ''))
                loc_sim = self._calculate_similarity(loc1, loc2)
                
                # Check if it's a potential duplicate
                if title_sim >= self.title_threshold and loc_sim >= self.location_threshold:
                    duplicates.append({
                        'event1_index': i,
                        'event2_index': j,
                        'event1': event1,
                        'event2': event2,
                        'title_similarity': round(title_sim, 3),
                        'location_similarity': round(loc_sim, 3),
                        'confidence': 'high' if title_sim > 0.95 else 'medium'
                    })
        
        return duplicates
    
    def deduplicate_events(self, events: List[Dict], strategy: str = 'hash') -> List[Dict]:
        """
        Remove duplicates from event list
        
        Args:
            events: List of events
            strategy: 'hash' for exact duplicates, 'fuzzy' for similar events
        
        Returns:
            List with duplicates removed
        """
        if strategy == 'hash':
            seen_hashes = set()
            unique_events = []
            
            for event in events:
                event_hash = self._generate_event_hash(event)
                if event_hash not in seen_hashes:
                    seen_hashes.add(event_hash)
                    unique_events.append(event)
            
            return unique_events
        
        elif strategy == 'fuzzy':
            # More complex - keep first occurrence of each fuzzy group
            duplicates = self.find_fuzzy_duplicates(events)
            indices_to_remove = set()
            
            for dup in duplicates:
                indices_to_remove.add(dup['event2_index'])
            
            return [event for idx, event in enumerate(events) if idx not in indices_to_remove]
        
        return events


class DataCleaner:
    """Cleans and normalizes event data"""
    
    @staticmethod
    def clean_title(title: str) -> str:
        """Clean and normalize event title"""
        if not title:
            return ""
        
        # Remove excessive whitespace
        title = ' '.join(title.split())
        
        # Remove common spam patterns
        spam_patterns = ['!!!', '***', '###', '@@@']
        for pattern in spam_patterns:
            title = title.replace(pattern, '')
        
        # Capitalize properly
        title = title.title()
        
        return title.strip()
    
    @staticmethod
    def clean_location(location: str) -> str:
        """Clean and normalize location"""
        if not location:
            return ""
        
        # Remove extra whitespace
        location = ' '.join(location.split())
        
        # Standardize common abbreviations
        replacements = {
            'st.': 'Street',
            'ave.': 'Avenue',
            'blvd.': 'Boulevard',
            'rd.': 'Road',
            'dr.': 'Drive'
        }
        
        location_lower = location.lower()
        for abbrev, full in replacements.items():
            location_lower = location_lower.replace(abbrev, full)
        
        return location_lower.title().strip()
    
    @staticmethod
    def normalize_date(date_str: str) -> Optional[date]:
        """Normalize date string to date object"""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def clean_event(event: Dict) -> Dict:
        """Apply all cleaning operations to an event"""
        cleaned = event.copy()
        
        if 'title' in cleaned:
            cleaned['title'] = DataCleaner.clean_title(cleaned['title'])
        
        if 'location' in cleaned:
            cleaned['location'] = DataCleaner.clean_location(cleaned['location'])
        
        if 'date' in cleaned and isinstance(cleaned['date'], str):
            normalized_date = DataCleaner.normalize_date(cleaned['date'])
            if normalized_date:
                cleaned['date'] = normalized_date.isoformat()
        
        return cleaned


# Convenience function for running quality checks
async def run_quality_audit(events: List[Dict]) -> Dict:
    """
    Run complete quality audit on events
    
    Returns:
        Dict with quality report and duplicate analysis
    """
    # Check quality
    quality_checker = DataQualityChecker()
    quality_report = await quality_checker.analyze_events(events)
    
    # Check duplicates
    duplicate_detector = DuplicateDetector()
    exact_duplicates = duplicate_detector.find_exact_duplicates(events)
    fuzzy_duplicates = duplicate_detector.find_fuzzy_duplicates(events)
    
    # Update report with duplicate count
    quality_report.duplicates_found = len(exact_duplicates) + len(fuzzy_duplicates)
    
    return {
        'quality': quality_report,
        'exact_duplicates': exact_duplicates,
        'fuzzy_duplicates': fuzzy_duplicates,
        'total_issues': len(quality_report.suspicious_events) + len(exact_duplicates) + len(fuzzy_duplicates)
    }


if __name__ == "__main__":
    # Test data quality checker
    test_events = [
        {
            'title': 'Underground Rave Party',
            'description': 'Join us for an amazing night of electronic music',
            'location': 'Warehouse District, LA',
            'date': '2026-02-15',
            'link': 'https://eventbrite.com/event/123'
        },
        {
            'title': 'Underground Rave Party',  # Duplicate
            'description': 'Join us for an amazing night',
            'location': 'Warehouse District, LA',
            'date': '2026-02-15',
            'link': 'https://eventbrite.com/event/123'
        },
        {
            'title': 'Short',  # Quality issue - too short
            'description': 'Bad',
            'location': 'LA',
            'date': '2026-02-15',
            'link': 'not-a-url'  # Quality issue
        }
    ]
    
    async def test():
        print("Running data quality audit...")
        result = await run_quality_audit(test_events)
        
        print(f"\nQuality Score: {result['quality'].quality_score}/100")
        print(f"Total Events: {result['quality'].total_events}")
        print(f"Exact Duplicates: {len(result['exact_duplicates'])}")
        print(f"Fuzzy Duplicates: {len(result['fuzzy_duplicates'])}")
        print(f"Suspicious Events: {len(result['quality'].suspicious_events)}")
        
        if result['quality'].suspicious_events:
            print("\nIssues Found:")
            for item in result['quality'].suspicious_events:
                print(f"  - {item['event'].get('title', 'Untitled')}: {item['issues']}")
    
    asyncio.run(test())
