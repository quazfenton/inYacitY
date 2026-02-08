#!/usr/bin/env python3
"""
Configuration loader for all scrapers
Provides centralized configuration management
"""

import json
import os
from typing import Dict, Any, Optional


class Config:
    """Global configuration handler"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load()
    
    def load(self, config_file: str = "config.json") -> None:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self._config = json.load(f)
                print(f"✓ Config loaded from {config_file}")
            else:
                print(f"⚠ Config file not found: {config_file}, using defaults")
                self._config = self._get_defaults()
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing config.json: {e}")
            self._config = self._get_defaults()
        except Exception as e:
            print(f"✗ Error loading config: {e}")
            self._config = self._get_defaults()
    
    @staticmethod
    def _get_defaults() -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "LOCATION": "ca--los-angeles",
            "BROWSER": {
                "HEADLESS": True,
                "TIMEOUT": 30000,
                "WAIT_TIME": 2000
            },
            "SCRAPER_SETTINGS": {
                "EVENTBRITE": {"enabled": True},
                "MEETUP": {"enabled": True},
                "LUMA": {"enabled": True},
                "DICE_FM": {"enabled": True},
                "RA_CO": {"enabled": True},
                "POSH_VIP": {"enabled": False}
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_location(self) -> str:
        """Get current location"""
        return self.get('LOCATION', 'ca--los-angeles')
    
    def get_browser_settings(self) -> Dict[str, Any]:
        """Get browser configuration"""
        return self.get('BROWSER', {})
    
    def get_scraper_config(self, scraper_name: str) -> Dict[str, Any]:
        """Get configuration for specific scraper"""
        scraper_name_upper = scraper_name.upper()
        return self.get(f'SCRAPER_SETTINGS.{scraper_name_upper}', {})
    
    def is_scraper_enabled(self, scraper_name: str) -> bool:
        """Check if scraper is enabled"""
        config = self.get_scraper_config(scraper_name)
        return config.get('enabled', False)
    
    def get_city_map(self, scraper_name: str) -> Dict[str, str]:
        """Get city mapping for specific scraper"""
        config = self.get_scraper_config(scraper_name)
        return config.get('city_map', {})
    
    def get_supported_locations(self) -> list:
        """Get list of supported locations"""
        return self.get('SUPPORTED_LOCATIONS', [])
    
    def get_price_filter(self) -> Dict[str, int]:
        """Get price filter settings"""
        return self.get('DATA.PRICE_FILTER', {})
    
    def get_output_settings(self) -> Dict[str, Any]:
        """Get output configuration"""
        return self.get('OUTPUT', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Return full configuration as dictionary"""
        return self._config.copy()


def get_config() -> Config:
    """Get global config instance"""
    return Config()
