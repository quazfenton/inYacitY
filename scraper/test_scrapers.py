#!/usr/bin/env python3
"""
Comprehensive Scraper Testing and Optimization Tool

Tests all scrapers and provides:
- Output validation
- Selector effectiveness analysis
- Data quality metrics
- Deduplication statistics
- Parsing error reporting
- Recommendations for improvements
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import re


class ScraperTestReport:
    """Generate and analyze scraper test results"""
    
    def __init__(self, scraper_name: str):
        self.scraper_name = scraper_name
        self.events: List[Dict] = []
        self.errors: List[str] = []
        self.metrics: Dict = {}
        self.duplicates: List[tuple] = []
        self.start_time = datetime.now()

    def add_event(self, event: Dict) -> None:
        """Add event to report"""
        self.events.append(event)

    def add_error(self, error: str) -> None:
        """Add error to report"""
        self.errors.append(error)

    def analyze(self) -> Dict:
        """Analyze scraper performance"""
        
        # Basic stats
        total = len(self.events)
        
        # Data completeness
        complete_fields = {
            'title': sum(1 for e in self.events if e.get('title')),
            'date': sum(1 for e in self.events if e.get('date')),
            'time': sum(1 for e in self.events if e.get('time') and e['time'] != 'TBA'),
            'location': sum(1 for e in self.events if e.get('location')),
            'link': sum(1 for e in self.events if e.get('link')),
            'description': sum(1 for e in self.events if e.get('description')),
            'price': sum(1 for e in self.events if 'price' in e),
            'image': sum(1 for e in self.events if e.get('image') or e.get('image_url'))
        }
        
        # Calculate completion rates
        completeness_rate = {
            field: round((count / total * 100) if total > 0 else 0, 1)
            for field, count in complete_fields.items()
        }
        
        # Detect duplicates
        seen_links = {}
        for i, event in enumerate(self.events):
            link = event.get('link', '')
            if link:
                if link in seen_links:
                    self.duplicates.append((seen_links[link], i))
                else:
                    seen_links[link] = i
        
        # Price analysis
        prices = [e.get('price', 0) for e in self.events if 'price' in e]
        free_events = sum(1 for p in prices if p == 0)
        
        # Date validation
        valid_dates = 0
        invalid_dates = []
        for event in self.events:
            date = event.get('date', '')
            if date:
                if re.match(r'\d{4}-\d{2}-\d{2}', str(date)):
                    valid_dates += 1
                else:
                    invalid_dates.append((event.get('title', 'Unknown'), date))
        
        # Time validation
        valid_times = 0
        invalid_times = []
        for event in self.events:
            time = event.get('time', '')
            if time and time != 'TBA':
                if re.match(r'\d{1,2}:\d{2}|TBA', str(time)):
                    valid_times += 1
                else:
                    invalid_times.append((event.get('title', 'Unknown'), time))
        
        # Location analysis
        location_sample = [e.get('location', 'Unknown')[:50] for e in self.events[:5]]
        
        self.metrics = {
            'total_events': total,
            'errors': len(self.errors),
            'duplicates': len(self.duplicates),
            'completeness_rate': completeness_rate,
            'data_quality': {
                'free_events': free_events,
                'paid_events': len(prices) - free_events,
                'valid_dates': valid_dates,
                'invalid_dates': len(invalid_dates),
                'valid_times': valid_times,
                'invalid_times': len(invalid_times),
                'avg_description_length': round(
                    sum(len(e.get('description', '')) for e in self.events) / total if total > 0 else 0
                )
            },
            'data_samples': {
                'title_samples': [e.get('title', 'Unknown')[:50] for e in self.events[:3]],
                'location_samples': location_sample,
                'date_samples': [e.get('date', 'TBA') for e in self.events[:3]]
            }
        }
        
        return self.metrics

    def generate_report(self) -> str:
        """Generate human-readable report"""
        report = []
        report.append("\n" + "="*80)
        report.append(f"SCRAPER TEST REPORT: {self.scraper_name.upper()}")
        report.append("="*80)
        
        # Summary
        report.append(f"\nExecution Time: {datetime.now() - self.start_time}")
        report.append(f"Total Events: {len(self.events)}")
        report.append(f"Errors: {len(self.errors)}")
        report.append(f"Duplicates Found: {len(self.duplicates)}")
        
        if self.metrics:
            # Completeness
            report.append("\n--- DATA COMPLETENESS ---")
            rates = self.metrics.get('completeness_rate', {})
            for field, rate in sorted(rates.items()):
                status = "✓" if rate >= 80 else "✗" if rate < 50 else "~"
                report.append(f"  {status} {field:15} {rate:5.1f}%")
            
            # Data Quality
            quality = self.metrics.get('data_quality', {})
            report.append("\n--- DATA QUALITY ---")
            report.append(f"  Free Events: {quality.get('free_events', 0)}")
            report.append(f"  Paid Events: {quality.get('paid_events', 0)}")
            report.append(f"  Valid Dates: {quality.get('valid_dates', 0)}")
            report.append(f"  Invalid Dates: {quality.get('invalid_dates', 0)}")
            report.append(f"  Valid Times: {quality.get('valid_times', 0)}")
            report.append(f"  Invalid Times: {quality.get('invalid_times', 0)}")
            report.append(f"  Avg Description Length: {quality.get('avg_description_length', 0)} chars")
            
            # Samples
            report.append("\n--- DATA SAMPLES ---")
            samples = self.metrics.get('data_samples', {})
            if samples.get('title_samples'):
                report.append(f"  Title: {samples['title_samples'][0]}")
            if samples.get('location_samples'):
                report.append(f"  Location: {samples['location_samples'][0]}")
            if samples.get('date_samples'):
                report.append(f"  Date: {samples['date_samples'][0]}")
        
        # Errors
        if self.errors:
            report.append("\n--- ERRORS ---")
            for error in self.errors[:5]:  # Show first 5
                report.append(f"  • {error}")
            if len(self.errors) > 5:
                report.append(f"  ... and {len(self.errors) - 5} more errors")
        
        # Duplicates
        if self.duplicates:
            report.append("\n--- DUPLICATES ---")
            for idx1, idx2 in self.duplicates[:3]:
                link1 = self.events[idx1].get('link', 'N/A')
                link2 = self.events[idx2].get('link', 'N/A')
                if link1 == link2:
                    report.append(f"  Duplicate: {link1[:60]}")
            if len(self.duplicates) > 3:
                report.append(f"  ... {len(self.duplicates) - 3} more duplicates")
        
        report.append("\n" + "="*80)
        return "\n".join(report)

    def save_json(self, filename: str) -> None:
        """Save report as JSON"""
        data = {
            'scraper': self.scraper_name,
            'timestamp': self.start_time.isoformat(),
            'metrics': self.metrics,
            'events_sample': self.events[:10],  # First 10 events
            'total_events': len(self.events),
            'duplicates': len(self.duplicates),
            'errors': self.errors[:10]  # First 10 errors
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class ScraperTester:
    """Test runner for all scrapers"""
    
    def __init__(self):
        self.results: Dict[str, ScraperTestReport] = {}

    async def test_luma(self) -> ScraperTestReport:
        """Test Luma scraper"""
        report = ScraperTestReport('luma')
        
        try:
            # Load existing luma events
            if os.path.exists('luma_events.json'):
                with open('luma_events.json', 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        report.add_event(event)
            else:
                report.add_error("luma_events.json not found - run scraper first")
        
        except Exception as e:
            report.add_error(f"Error loading luma events: {str(e)}")
        
        report.analyze()
        return report

    async def test_meetup(self) -> ScraperTestReport:
        """Test Meetup scraper"""
        report = ScraperTestReport('meetup')
        
        try:
            # Load existing meetup events
            if os.path.exists('meetup_events.json'):
                with open('meetup_events.json', 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        report.add_event(event)
            else:
                report.add_error("meetup_events.json not found - run scraper first")
        
        except Exception as e:
            report.add_error(f"Error loading meetup events: {str(e)}")
        
        report.analyze()
        return report

    async def test_eventbrite(self) -> ScraperTestReport:
        """Test Eventbrite scraper"""
        report = ScraperTestReport('eventbrite')
        
        try:
            # Load existing eventbrite events
            if os.path.exists('all_events.json'):
                with open('all_events.json', 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        if event.get('source') == 'Eventbrite':
                            report.add_event(event)
            else:
                report.add_error("all_events.json not found - run scraper first")
        
        except Exception as e:
            report.add_error(f"Error loading eventbrite events: {str(e)}")
        
        report.analyze()
        return report

    async def test_dice_fm(self) -> ScraperTestReport:
        """Test Dice.fm scraper"""
        report = ScraperTestReport('dice_fm')
        
        try:
            # Load existing dice_fm events
            if os.path.exists('dice_events.json'):
                with open('dice_events.json', 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        report.add_event(event)
            else:
                report.add_error("dice_events.json not found - run scraper first")
        
        except Exception as e:
            report.add_error(f"Error loading dice_fm events: {str(e)}")
        
        report.analyze()
        return report

    async def test_ra_co(self) -> ScraperTestReport:
        """Test RA.co scraper"""
        report = ScraperTestReport('ra_co')
        
        try:
            # Load existing ra_co events
            if os.path.exists('ra_co_events.json'):
                with open('ra_co_events.json', 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        report.add_event(event)
            else:
                report.add_error("ra_co_events.json not found - run scraper first")
        
        except Exception as e:
            report.add_error(f"Error loading ra_co events: {str(e)}")
        
        report.analyze()
        return report

    async def test_posh_vip(self) -> ScraperTestReport:
        """Test Posh.vip scraper"""
        report = ScraperTestReport('posh_vip')
        
        try:
            # Load existing posh_vip events
            if os.path.exists('posh_vip_events.json'):
                with open('posh_vip_events.json', 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        report.add_event(event)
            else:
                report.add_error("posh_vip_events.json not found - run scraper first")
        
        except Exception as e:
            report.add_error(f"Error loading posh_vip events: {str(e)}")
        
        report.analyze()
        return report

    async def run_all_tests(self) -> None:
        """Run all scraper tests"""
        print("\n" + "="*80)
        print("SCRAPER TESTING SUITE")
        print("="*80)
        
        scrapers = [
            ('luma', self.test_luma),
            ('meetup', self.test_meetup),
            ('eventbrite', self.test_eventbrite),
            ('dice_fm', self.test_dice_fm),
            ('ra_co', self.test_ra_co),
            ('posh_vip', self.test_posh_vip)
        ]
        
        for name, test_func in scrapers:
            try:
                print(f"\nTesting {name.upper()}...")
                report = await test_func()
                self.results[name] = report
                print(report.generate_report())
            except Exception as e:
                print(f"Error testing {name}: {str(e)}")

    def generate_summary(self) -> str:
        """Generate overall summary"""
        summary = []
        summary.append("\n" + "="*80)
        summary.append("OVERALL SUMMARY")
        summary.append("="*80)
        
        summary.append("\n--- SCRAPER STATUS ---")
        for name, report in self.results.items():
            status = "✓" if len(report.events) > 0 and len(report.errors) == 0 else "✗"
            count = len(report.events)
            errors = len(report.errors)
            summary.append(f"  {status} {name:15} {count:5} events, {errors:3} errors")
        
        summary.append("\n--- RECOMMENDATIONS ---")
        
        # Analyze completeness issues
        for name, report in self.results.items():
            if report.metrics:
                rates = report.metrics.get('completeness_rate', {})
                issues = [f for f, r in rates.items() if r < 80]
                if issues:
                    summary.append(f"\n  {name.upper()}:")
                    for issue in issues:
                        rate = rates[issue]
                        summary.append(f"    • {issue}: {rate}% (needs improvement)")
        
        summary.append("\n" + "="*80)
        return "\n".join(summary)

    def save_all_reports(self, output_dir: str = 'scraper_tests') -> None:
        """Save all reports to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        for name, report in self.results.items():
            # Save JSON
            json_path = os.path.join(output_dir, f'{name}_test_report.json')
            report.save_json(json_path)
            print(f"Saved: {json_path}")
            
            # Save text report
            text_path = os.path.join(output_dir, f'{name}_test_report.txt')
            with open(text_path, 'w') as f:
                f.write(report.generate_report())
            print(f"Saved: {text_path}")
        
        # Save summary
        summary_path = os.path.join(output_dir, 'SUMMARY.txt')
        with open(summary_path, 'w') as f:
            f.write(self.generate_summary())
        print(f"Saved: {summary_path}")


async def main():
    """Main test runner"""
    tester = ScraperTester()
    await tester.run_all_tests()
    print(tester.generate_summary())
    tester.save_all_reports()


if __name__ == "__main__":
    asyncio.run(main())
