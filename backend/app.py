"""
Main Flask application
Integrates all APIs, blueprints, and configurations
Production-ready setup with all features:
- Event scraper sync
- Email subscriptions
- Event RSVPs with calendar integration
- Event comments with rate limiting
"""

import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

# Add paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(project_root))


def create_app(config_name: str = 'production'):
    """
    Application factory
    
    Args:
        config_name: 'development', 'staging', or 'production'
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['JSON_SORT_KEYS'] = False
    
    # Environment-specific config
    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = False
    elif config_name == 'staging':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    else:  # production
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3000",
                "http://localhost:5173",
                os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    from backend.api.scraper_api import scraper_api
    app.register_blueprint(scraper_api)
    
    # Optional: Register locations API if available
    try:
        from backend.api.locations_api import locations_api
        app.register_blueprint(locations_api)
    except ImportError:
        print("Warning: locations_api not available")
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """API health check"""
        return jsonify({
            'status': 'healthy',
            'service': 'inyAcity Event Scraper API',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': config_name,
            'endpoints': {
                'scraper': '/api/scraper/*',
                'locations': '/api/locations/*'
            }
        }), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def index():
        """API information"""
        return jsonify({
            'name': 'inyAcity Event Scraper API',
            'version': '1.0.0',
            'description': 'Event scraping, RSVP, comments, and email subscriptions',
            'features': [
                'Event scraping from multiple sources',
                'Database synchronization with Supabase',
                'Email subscriptions grouped by city',
                'Event RSVPs with calendar integration',
                'Event comments with rate limiting',
                'Geolocation support'
            ],
            'endpoints': {
                'health': '/health',
                'scraper': '/api/scraper',
                'locations': '/api/locations'
            },
            'documentation': {
                from flask import Flask, jsonify, request
                from flask_cors import CORS
                from datetime import datetime

                # Add paths
                project_root = os.path.dirname(os.path.abspath(__file__))
                sys.path.insert(0, project_root)
                sys.path.insert(0, os.path.dirname(project_root))


                def create_app(config_name: str = 'production'):
                    """
                    Application factory
    
                    Args:
                        config_name: 'development', 'staging', or 'production'
    
                    Returns:
                        Configured Flask application
                    """
                    app = Flask(__name__)
    
                    # Configuration
                    app.config['JSON_SORT_KEYS'] = False
    
                    # Environment-specific config
                    if config_name == 'development':
                        app.config['DEBUG'] = True
                        app.config['TESTING'] = False
                    elif config_name == 'staging':
                        app.config['DEBUG'] = False
                        app.config['TESTING'] = False
                    else:  # production
                        app.config['DEBUG'] = False
                        app.config['TESTING'] = False
    
                    # CORS configuration
                    CORS(app, resources={
                        r"/api/*": {
                            "origins": [
                                "http://localhost:3000",
                                "http://localhost:5173",
                                os.environ.get('FRONTEND_URL', 'http://localhost:3000')
                            ],
                            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                            "allow_headers": ["Content-Type", "Authorization"]
                        }
                    })
    
                    # Register blueprints
                    from backend.api.scraper_api import scraper_api
                    app.register_blueprint(scraper_api)
    
                    # Optional: Register locations API if available
                    try:
                        from backend.api.locations_api import locations_api
                        app.register_blueprint(locations_api)
                    except ImportError:
                        print("Warning: locations_api not available")
    
                    # Health check endpoint
                    @app.route('/health', methods=['GET'])
                    def health_check():
                        """API health check"""
                        return jsonify({
                            'status': 'healthy',
                            'service': 'inyAcity Event Scraper API',
                            'timestamp': datetime.utcnow().isoformat(),
                            'environment': config_name,
                            'endpoints': {
                                'scraper': '/api/scraper/*',
                                'locations': '/api/locations/*'
                            }
                        }), 200
    
                    # Root endpoint
                    @app.route('/', methods=['GET'])
                    def index():
                        """API information"""
                        return jsonify({
                            'name': 'inyAcity Event Scraper API',
                            'version': '1.0.0',
                            'description': 'Event scraping, RSVP, comments, and email subscriptions',
                            'features': [
                                'Event scraping from multiple sources',
                                'Database synchronization with Supabase',
                                'Email subscriptions grouped by city',
                                'Event RSVPs with calendar integration',
                                'Event comments with rate limiting',
                                'Geolocation support'
                            ],
                            'endpoints': {
                                'health': '/health',
                                'scraper': '/api/scraper',
                                'locations': '/api/locations'
                            },
                            'documentation': {
                                'sync': 'DB_SYNC_INTEGRATION_GUIDE.md',
                                'rsvp': 'RSVP_INTEGRATION_GUIDE.md',
                                'comments': 'COMMENTS_INTEGRATION_GUIDE.md'
                            }
                        }), 200
    
                    # Error handlers
                    @app.errorhandler(400)
                    def bad_request(error):
                        return jsonify({
                            'success': False,
                            'message': 'Bad request',
                            'error': str(error)
                        }), 400
    
                    @app.errorhandler(404)
                    def not_found(error):
                        return jsonify({
                            'success': False,
                            'message': 'Endpoint not found',
                            'path': request.path
                        }), 404
    
                    @app.errorhandler(429)
                    def rate_limited(error):
                        return jsonify({
            'success': False,
            'message': 'Rate limit exceeded',
            'error': str(error)
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'error': str(error) if app.config['DEBUG'] else 'Server error'
        }), 500
    
    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)
