-- Location-based system tables and schema
-- Supports user location preferences, proximity-based queries, and event filtering

-- ============================================================================
-- LOCATIONS TABLE
-- ============================================================================
-- Master location data: major cities, secondary cities, towns

CREATE TABLE IF NOT EXISTS locations (
  id VARCHAR(50) PRIMARY KEY,
  code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  tier VARCHAR(20) NOT NULL, -- 'major', 'secondary', 'town', 'region'
  latitude DECIMAL(10, 8) NOT NULL,
  longitude DECIMAL(11, 8) NOT NULL,
  state VARCHAR(10),
  country VARCHAR(2), -- ISO country code
  population INTEGER,
  parent_city_code VARCHAR(50), -- For secondary cities, reference to major city
  timezone VARCHAR(50),
  metadata JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_code (code),
  INDEX idx_tier (tier),
  INDEX idx_country (country),
  INDEX idx_coordinates (latitude, longitude),
  INDEX idx_parent_city (parent_city_code),
  FOREIGN KEY (parent_city_code) REFERENCES locations(code)
);

-- ============================================================================
-- USER_LOCATION_PREFERENCES TABLE
-- ============================================================================
-- Store user's location preferences and auto-detection settings

CREATE TABLE IF NOT EXISTS user_location_preferences (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL UNIQUE,
  major_city_code VARCHAR(50) NOT NULL,
  secondary_latitude DECIMAL(10, 8),
  secondary_longitude DECIMAL(11, 8),
  auto_detect BOOLEAN DEFAULT TRUE,
  preferred_radius_miles FLOAT DEFAULT 25.0,
  ip_address VARCHAR(45),
  user_agent TEXT,
  device_type VARCHAR(50), -- 'desktop', 'mobile', 'tablet'
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_user_id (user_id),
  INDEX idx_major_city_code (major_city_code),
  INDEX idx_last_updated (last_updated),
  FOREIGN KEY (major_city_code) REFERENCES locations(code)
);

-- ============================================================================
-- LOCATION_HISTORY TABLE
-- ============================================================================
-- Track user's location history for analytics and recommendations

CREATE TABLE IF NOT EXISTS location_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  location_code VARCHAR(50),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  detection_method VARCHAR(50), -- 'browser_geolocation', 'ip_geolocation', 'manual'
  accuracy_meters INT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  session_id VARCHAR(100),
  
  INDEX idx_user_id (user_id),
  INDEX idx_timestamp (timestamp),
  INDEX idx_location_code (location_code),
  INDEX idx_session_id (session_id),
  FOREIGN KEY (location_code) REFERENCES locations(code)
);

-- ============================================================================
-- LOCATION_ALIASES TABLE
-- ============================================================================
-- Support alternative names for locations (e.g., "NYC" for "New York")

CREATE TABLE IF NOT EXISTS location_aliases (
  id INT AUTO_INCREMENT PRIMARY KEY,
  location_code VARCHAR(50) NOT NULL,
  alias VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE KEY unique_alias (location_code, alias),
  INDEX idx_alias (alias),
  FOREIGN KEY (location_code) REFERENCES locations(code)
);

-- ============================================================================
-- NEARBY_LOCATIONS CACHE TABLE
-- ============================================================================
-- Cache nearby locations for quick proximity queries

CREATE TABLE IF NOT EXISTS nearby_locations_cache (
  id INT AUTO_INCREMENT PRIMARY KEY,
  center_location_code VARCHAR(50) NOT NULL,
  nearby_location_code VARCHAR(50) NOT NULL,
  distance_miles FLOAT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  
  UNIQUE KEY unique_pair (center_location_code, nearby_location_code),
  INDEX idx_center (center_location_code),
  INDEX idx_expires (expires_at),
  FOREIGN KEY (center_location_code) REFERENCES locations(code),
  FOREIGN KEY (nearby_location_code) REFERENCES locations(code)
);

-- ============================================================================
-- LOCATION_COORDINATES_INDEX TABLE
-- ============================================================================
-- Spatial index for efficient proximity searches (if database supports)

CREATE TABLE IF NOT EXISTS location_search_index (
  id INT AUTO_INCREMENT PRIMARY KEY,
  location_code VARCHAR(50) NOT NULL UNIQUE,
  lat_grid_10 INT,          -- Grid cell (0.1 degree)
  lon_grid_10 INT,
  lat_grid_100 INT,         -- Grid cell (0.01 degree / ~1 km)
  lon_grid_100 INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_grid_10 (lat_grid_10, lon_grid_10),
  INDEX idx_grid_100 (lat_grid_100, lon_grid_100),
  FOREIGN KEY (location_code) REFERENCES locations(code)
);

-- ============================================================================
-- USER_LOCATION_RECOMMENDATIONS TABLE
-- ============================================================================
-- Store personalized location recommendations based on user history

CREATE TABLE IF NOT EXISTS user_location_recommendations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  recommended_location_code VARCHAR(50) NOT NULL,
  score FLOAT DEFAULT 0.0,
  reason VARCHAR(255), -- 'proximity', 'frequency', 'similarity', etc.
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  
  INDEX idx_user_id (user_id),
  INDEX idx_score (score),
  INDEX idx_expires (expires_at),
  FOREIGN KEY (recommended_location_code) REFERENCES locations(code)
);

-- ============================================================================
-- LOCATION_EVENTS_SUMMARY TABLE
-- ============================================================================
-- Pre-aggregated event counts by location for quick filtering

CREATE TABLE IF NOT EXISTS location_events_summary (
  id INT AUTO_INCREMENT PRIMARY KEY,
  location_code VARCHAR(50) NOT NULL UNIQUE,
  total_events INT DEFAULT 0,
  free_events INT DEFAULT 0,
  paid_events INT DEFAULT 0,
  upcoming_30_days INT DEFAULT 0,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (location_code) REFERENCES locations(code)
);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: All major cities with event counts
CREATE OR REPLACE VIEW major_cities_with_stats AS
SELECT
  l.code,
  l.name,
  l.latitude,
  l.longitude,
  l.state,
  l.country,
  l.population,
  l.timezone,
  COALESCE(les.total_events, 0) as total_events,
  COALESCE(les.free_events, 0) as free_events,
  COALESCE(les.upcoming_30_days, 0) as upcoming_30_days,
  (SELECT COUNT(*) FROM user_location_preferences WHERE major_city_code = l.code) as user_count
FROM locations l
LEFT JOIN location_events_summary les ON l.code = les.location_code
WHERE l.tier = 'major'
ORDER BY l.population DESC;

-- View: Users and their preferred locations
CREATE OR REPLACE VIEW user_location_preferences_view AS
SELECT
  ulp.user_id,
  ulp.major_city_code,
  l.name as major_city_name,
  ulp.secondary_latitude,
  ulp.secondary_longitude,
  ulp.auto_detect,
  ulp.preferred_radius_miles,
  ulp.device_type,
  ulp.last_updated,
  COUNT(lh.id) as location_checkins
FROM user_location_preferences ulp
LEFT JOIN locations l ON ulp.major_city_code = l.code
LEFT JOIN location_history lh ON ulp.user_id = lh.user_id
GROUP BY ulp.user_id, ulp.major_city_code;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Optimize distance-based queries
CREATE INDEX IF NOT EXISTS idx_locations_lat_lon ON locations (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_locations_tier_country ON locations (tier, country);

-- Optimize user preference lookups
CREATE INDEX IF NOT EXISTS idx_user_prefs_major_city ON user_location_preferences (major_city_code);
CREATE INDEX IF NOT EXISTS idx_user_prefs_auto_detect ON user_location_preferences (auto_detect);

-- Optimize history queries
CREATE INDEX IF NOT EXISTS idx_location_history_user_timestamp ON location_history (user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_location_history_location_timestamp ON location_history (location_code, timestamp);

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

-- Find nearby locations within X miles
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS find_nearby_locations(
  IN center_lat DECIMAL(10, 8),
  IN center_lon DECIMAL(11, 8),
  IN search_radius_miles INT
)
BEGIN
  SELECT
    l.code,
    l.name,
    l.latitude,
    l.longitude,
    l.tier,
    l.country,
    -- Haversine formula: distance in miles
    (
      3959 * acos(
        cos(radians(center_lat)) * cos(radians(l.latitude)) *
        cos(radians(l.longitude) - radians(center_lon)) +
        sin(radians(center_lat)) * sin(radians(l.latitude))
      )
    ) as distance_miles
  FROM locations l
  HAVING distance_miles <= search_radius_miles
  ORDER BY distance_miles ASC;
END$$

DELIMITER ;

-- Update event counts for location
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS update_location_event_counts(
  IN location_code_param VARCHAR(50)
)
BEGIN
  DECLARE event_total INT;
  DECLARE event_free INT;
  DECLARE event_upcoming INT;

  -- Count total events
  SET event_total = (
    SELECT COUNT(*) FROM events
    WHERE location_code = location_code_param
  );

  -- Count free events
  SET event_free = (
    SELECT COUNT(*) FROM events
    WHERE location_code = location_code_param AND price = 0
  );

  -- Count upcoming events (next 30 days)
  SET event_upcoming = (
    SELECT COUNT(*) FROM events
    WHERE location_code = location_code_param
    AND event_date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)
  );

  -- Update or insert into summary table
  INSERT INTO location_events_summary
    (location_code, total_events, free_events, upcoming_30_days)
  VALUES
    (location_code_param, event_total, event_free, event_upcoming)
  ON DUPLICATE KEY UPDATE
    total_events = event_total,
    free_events = event_free,
    upcoming_30_days = event_upcoming;
END$$

DELIMITER ;

-- ============================================================================
-- INITIAL DATA: POPULATE MAJOR CITIES
-- ============================================================================

-- Insert major cities (from scraper configuration)
INSERT INTO locations (id, code, name, tier, latitude, longitude, state, country, population, timezone) VALUES
-- United States - California
('ca-la', 'ca--los-angeles', 'Los Angeles, CA', 'major', 34.0522, -118.2437, 'CA', 'US', 3979576, 'America/Los_Angeles'),
('ca-sf', 'ca--san-francisco', 'San Francisco, CA', 'major', 37.7749, -122.4194, 'CA', 'US', 873965, 'America/Los_Angeles'),
('ca-sd', 'ca--san-diego', 'San Diego, CA', 'major', 32.7157, -117.1611, 'CA', 'US', 1423851, 'America/Los_Angeles'),
-- United States - Other States
('co-denver', 'co--denver', 'Denver, CO', 'major', 39.7392, -104.9903, 'CO', 'US', 727211, 'America/Denver'),
('dc-wash', 'dc--washington', 'Washington, DC', 'major', 38.9072, -77.0369, 'DC', 'US', 705749, 'America/New_York'),
('fl-miami', 'fl--miami', 'Miami, FL', 'major', 25.7617, -80.1918, 'FL', 'US', 442241, 'America/New_York'),
('ga-atlanta', 'ga--atlanta', 'Atlanta, GA', 'major', 33.7490, -84.3880, 'GA', 'US', 498044, 'America/New_York'),
('il-chicago', 'il--chicago', 'Chicago, IL', 'major', 41.8781, -87.6298, 'IL', 'US', 2693976, 'America/Chicago'),
('ma-boston', 'ma--boston', 'Boston, MA', 'major', 42.3601, -71.0589, 'MA', 'US', 692600, 'America/New_York'),
('nv-vegas', 'nv--las-vegas', 'Las Vegas, NV', 'major', 36.1699, -115.1398, 'NV', 'US', 644018, 'America/Los_Angeles'),
('ny-nyc', 'ny--new-york', 'New York, NY', 'major', 40.7128, -74.0060, 'NY', 'US', 8398748, 'America/New_York'),
('pa-philly', 'pa--philadelphia', 'Philadelphia, PA', 'major', 39.9526, -75.1652, 'PA', 'US', 1602494, 'America/New_York'),
('tx-austin', 'tx--austin', 'Austin, TX', 'major', 30.2672, -97.7431, 'TX', 'US', 961855, 'America/Chicago'),
('tx-dallas', 'tx--dallas', 'Dallas, TX', 'major', 32.7767, -96.7970, 'TX', 'US', 1304379, 'America/Chicago'),
('tx-houston', 'tx--houston', 'Houston, TX', 'major', 29.7604, -95.3698, 'TX', 'US', 2320268, 'America/Chicago'),
('ut-slc', 'ut--salt-lake-city', 'Salt Lake City, UT', 'major', 40.7608, -111.8910, 'UT', 'US', 199723, 'America/Denver'),
('wa-seattle', 'wa--seattle', 'Seattle, WA', 'major', 47.6062, -122.3321, 'WA', 'US', 753675, 'America/Los_Angeles'),
-- Canada
('on-toronto', 'on--toronto', 'Toronto, ON', 'major', 43.6532, -79.3832, 'ON', 'CA', 2930000, 'America/Toronto')
ON DUPLICATE KEY UPDATE name=name;

-- Insert location aliases for quick search
INSERT INTO location_aliases (location_code, alias) VALUES
('ca--los-angeles', 'LA'),
('ca--los-angeles', 'Los Angeles'),
('ca--san-francisco', 'SF'),
('ca--san-francisco', 'San Francisco'),
('ny--new-york', 'NYC'),
('ny--new-york', 'New York'),
('tx--houston', 'Houston'),
('il--chicago', 'Chicago'),
('dc--washington', 'DC'),
('dc--washington', 'Washington'),
('fl--miami', 'Miami'),
('ma--boston', 'Boston'),
('pa--philadelphia', 'Philly'),
('wa--seattle', 'Seattle'),
('on--toronto', 'Toronto')
ON DUPLICATE KEY UPDATE alias=alias;
