import os

# Supported locations (city IDs)
SUPPORTED_LOCATIONS = [
    'ca--los-angeles',
    'ny--new-york',
    'dc--washington',
    'fl--miami',
    'tx--houston',
    'il--chicago',
    'az--phoenix',
    'pa--philadelphia',
    'tx--san-antonio',
    'ca--san-diego',
    'tx--dallas',
    'ca--san-jose'
]

# Configuration dictionary
CONFIG = {
    'SUPPORTED_LOCATIONS': SUPPORTED_LOCATIONS,
    'SCRAPER': {
        'TIMEOUT': 30,
        'RETRIES': 3
    }
}

def load_config():
    """Load configuration from environment or file"""
    return CONFIG
