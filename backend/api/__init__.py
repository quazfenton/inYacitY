"""
Backend API package
Exports all API blueprints and utilities
"""

try:
    from api.scraper_api import scraper_api
    __all__ = ['scraper_api']
except ImportError:
    __all__ = []
