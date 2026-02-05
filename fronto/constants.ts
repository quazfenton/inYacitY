import { City } from './types';

// City mapping from backend city IDs to frontend display format
export const CITY_MAPPING: Record<string, City> = {
  'ca--los-angeles': { id: 'ca--los-angeles', name: 'LOS ANGELES', slug: 'los-angeles', coordinates: { lat: 34.0522, lng: -118.2437 } },
  'ny--new-york': { id: 'ny--new-york', name: 'NEW YORK', slug: 'new-york', coordinates: { lat: 40.7128, lng: -74.0060 } },
  'dc--washington': { id: 'dc--washington', name: 'WASHINGTON DC', slug: 'washington-dc', coordinates: { lat: 38.9072, lng: -77.0369 } },
  'fl--miami': { id: 'fl--miami', name: 'MIAMI', slug: 'miami', coordinates: { lat: 25.7617, lng: -80.1918 } },
  'tx--houston': { id: 'tx--houston', name: 'HOUSTON', slug: 'houston', coordinates: { lat: 29.7604, lng: -95.3698 } },
  'il--chicago': { id: 'il--chicago', name: 'CHICAGO', slug: 'chicago', coordinates: { lat: 41.8781, lng: -87.6298 } },
  'az--phoenix': { id: 'az--phoenix', name: 'PHOENIX', slug: 'phoenix', coordinates: { lat: 33.4484, lng: -112.0740 } },
  'pa--philadelphia': { id: 'pa--philadelphia', name: 'PHILADELPHIA', slug: 'philadelphia', coordinates: { lat: 39.9526, lng: -75.1652 } },
  'tx--san-antonio': { id: 'tx--san-antonio', name: 'SAN ANTONIO', slug: 'san-antonio', coordinates: { lat: 29.4241, lng: -98.4936 } },
  'ca--san-diego': { id: 'ca--san-diego', name: 'SAN DIEGO', slug: 'san-diego', coordinates: { lat: 32.7157, lng: -117.1611 } },
  'tx--dallas': { id: 'tx--dallas', name: 'DALLAS', slug: 'dallas', coordinates: { lat: 32.7767, lng: -96.7970 } },
  'tx--austin': { id: 'tx--austin', name: 'AUSTIN', slug: 'austin', coordinates: { lat: 30.2672, lng: -97.7431 } },
  'wa--seattle': { id: 'wa--seattle', name: 'SEATTLE', slug: 'seattle', coordinates: { lat: 47.6062, lng: -122.3321 } },
  'co--denver': { id: 'co--denver', name: 'DENVER', slug: 'denver', coordinates: { lat: 39.7392, lng: -104.9903 } },
  'ma--boston': { id: 'ma--boston', name: 'BOSTON', slug: 'boston', coordinates: { lat: 42.3601, lng: -71.0589 } },
  'ga--atlanta': { id: 'ga--atlanta', name: 'ATLANTA', slug: 'atlanta', coordinates: { lat: 33.7490, lng: -84.3880 } },
  'nv--las-vegas': { id: 'nv--las-vegas', name: 'LAS VEGAS', slug: 'las-vegas', coordinates: { lat: 36.1699, lng: -115.1398 } },
  'mi--detroit': { id: 'mi--detroit', name: 'DETROIT', slug: 'detroit', coordinates: { lat: 42.3314, lng: -83.0458 } },
  'or--portland': { id: 'or--portland', name: 'PORTLAND', slug: 'portland', coordinates: { lat: 45.5152, lng: -122.6784 } },
  'nc--charlotte': { id: 'nc--charlotte', name: 'CHARLOTTE', slug: 'charlotte', coordinates: { lat: 35.2271, lng: -80.8431 } },
  'tn--nashville': { id: 'tn--nashville', name: 'NASHVILLE', slug: 'nashville', coordinates: { lat: 36.1627, lng: -86.7816 } },
  'ok--oklahoma-city': { id: 'ok--oklahoma-city', name: 'OKLAHOMA CITY', slug: 'oklahoma-city', coordinates: { lat: 35.4676, lng: -97.5164 } },
  'la--new-orleans': { id: 'la--new-orleans', name: 'NEW ORLEANS', slug: 'new-orleans', coordinates: { lat: 29.9511, lng: -90.0715 } },
  'fl--orlando': { id: 'fl--orlando', name: 'ORLANDO', slug: 'orlando', coordinates: { lat: 28.5383, lng: -81.3792 } },
  'fl--tampa': { id: 'fl--tampa', name: 'TAMPA', slug: 'tampa', coordinates: { lat: 27.9506, lng: -82.4572 } },
  'ca--san-jose': { id: 'ca--san-jose', name: 'SAN JOSE', slug: 'san-jose', coordinates: { lat: 37.3382, lng: -121.8863 } },
  'ca--san-francisco': { id: 'ca--san-francisco', name: 'SAN FRANCISCO', slug: 'san-francisco', coordinates: { lat: 37.7749, lng: -122.4194 } },
  'ny--buffalo': { id: 'ny--buffalo', name: 'BUFFALO', slug: 'buffalo', coordinates: { lat: 42.8864, lng: -78.8784 } },
  'oh--columbus': { id: 'oh--columbus', name: 'COLUMBUS', slug: 'columbus', coordinates: { lat: 39.9612, lng: -82.9988 } },
  'oh--cleveland': { id: 'oh--cleveland', name: 'CLEVELAND', slug: 'cleveland', coordinates: { lat: 41.4993, lng: -81.6944 } },
  'in--indianapolis': { id: 'in--indianapolis', name: 'INDIANAPOLIS', slug: 'indianapolis', coordinates: { lat: 39.7684, lng: -86.1581 } },
  'mo--kansas-city': { id: 'mo--kansas-city', name: 'KANSAS CITY', slug: 'kansas-city', coordinates: { lat: 39.0997, lng: -94.5786 } },
  'mo--st-louis': { id: 'mo--st-louis', name: 'ST. LOUIS', slug: 'st-louis', coordinates: { lat: 38.6270, lng: -90.1994 } },
  'ca--sacramento': { id: 'ca--sacramento', name: 'SACRAMENTO', slug: 'sacramento', coordinates: { lat: 38.5816, lng: -121.4944 } },
  'tx--fort-worth': { id: 'tx--fort-worth', name: 'FORT WORTH', slug: 'fort-worth', coordinates: { lat: 32.7555, lng: -97.3308 } },
  'va--richmond': { id: 'va--richmond', name: 'RICHMOND', slug: 'richmond', coordinates: { lat: 37.5407, lng: -77.4360 } },
  'mn--minneapolis': { id: 'mn--minneapolis', name: 'MINNEAPOLIS', slug: 'minneapolis', coordinates: { lat: 44.9778, lng: -93.2650 } },
  'wi--milwaukee': { id: 'wi--milwaukee', name: 'MILWAUKEE', slug: 'milwaukee', coordinates: { lat: 43.0389, lng: -87.9065 } },
  'ky--louisville': { id: 'ky--louisville', name: 'LOUISVILLE', slug: 'louisville', coordinates: { lat: 38.2527, lng: -85.7585 } },
  'sc--charleston': { id: 'sc--charleston', name: 'CHARLESTON', slug: 'charleston-sc', coordinates: { lat: 32.7765, lng: -79.9311 } },
  'al--birmingham': { id: 'al--birmingham', name: 'BIRMINGHAM', slug: 'birmingham', coordinates: { lat: 33.5207, lng: -86.8025 } },
  'ut--salt-lake-city': { id: 'ut--salt-lake-city', name: 'SALT LAKE CITY', slug: 'salt-lake-city', coordinates: { lat: 40.7608, lng: -111.8910 } },
  'nm--albuquerque': { id: 'nm--albuquerque', name: 'ALBUQUERQUE', slug: 'albuquerque', coordinates: { lat: 35.0844, lng: -106.6504 } },
};

// Export as array for CitySelector component
export const CITIES: City[] = Object.values(CITY_MAPPING);

// API configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

