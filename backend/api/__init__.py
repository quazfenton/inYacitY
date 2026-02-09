"""
Backend API package
Exports all API blueprints and utilities
"""

from backend.api.scraper_api import scraper_api

__all__ = [
    'scraper_api',
]
