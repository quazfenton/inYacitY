#!/usr/bin/env python3
"""
Automation script to run scrapers for all supported locations
Rotates the LOCATION in config.json and runs scraper/run.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def run_scraper():
    """Run the main scraper script"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scraper/run.py...")
    # Using sys.executable to ensure we use the same python interpreter
    result = subprocess.run([sys.executable, os.path.join(BASE_DIR, 'run.py')], 
                            cwd=BASE_DIR, 
                            capture_output=False) # Show output in real-time
    return result.returncode == 0

def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: {CONFIG_PATH} not found.")
        return

    config = load_config()
    original_location = config.get('LOCATION', 'ca--los-angeles')
    supported_locations = config.get('SUPPORTED_LOCATIONS', [])

    if not supported_locations:
        print("No supported locations found in config.json.")
        return

    print(f"Starting all-location run for {len(supported_locations)} locations.")
    print(f"Original location: {original_location}")
    print("=" * 70)

    results = {}

    try:
        for i, location in enumerate(supported_locations):
            print(f"\n[Location {i+1}/{len(supported_locations)}] Targeting: {location}")
            
            # Update config
            config['LOCATION'] = location
            save_config(config)
            
            # Run scraper
            success = run_scraper()
            results[location] = "SUCCESS" if success else "FAILED"
            
            if not success:
                print(f"⚠️  Scraper failed for {location}")
            
            # Brief pause between locations to avoid overwhelming targets/browser issues
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\nStopped by user. Restoring original config...")
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
    finally:
        # Restore original location
        config['LOCATION'] = original_location
        save_config(config)
        print("\n" + "=" * 70)
        print("ALL-LOCATION RUN SUMMARY")
        print("=" * 70)
        for loc, res in results.items():
            print(f"{loc:.<40} {res}")
        print("=" * 70)
        print(f"Original location '{original_location}' restored.")

if __name__ == "__main__":
    main()
