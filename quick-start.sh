#!/bin/bash
# Quick Start Script for Nocturne Platform
# This script helps you get started quickly with Docker Compose

set -e

echo "=========================================="
echo "Nocturne Platform - Quick Start Script"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your configuration!"
    echo "   - Database credentials"
    echo "   - Email service (SMTP or SendGrid)"
    echo "   - Optional API keys for scrapers"
    echo ""
    read -p "Press Enter to continue, or Ctrl+C to edit .env first..."
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed"
    echo "   Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Stop existing containers
echo "Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Build and start services
echo ""
echo "Building and starting services..."
docker-compose up -d --build

# Wait for database to be ready
echo ""
echo "Waiting for database to be ready..."
database_ready=false
for i in {1..30}; do
    if docker exec nocturne_db psql -U nocturne -c "SELECT 1" &> /dev/null; then
        echo "✓ Database is ready!"
        database_ready=true
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

# Check if database became ready
if [ "$database_ready" = false ]; then
    echo "❌ Error: Database did not become ready within the timeout period"
    echo "   Please check the database logs: docker-compose logs postgres"
    exit 1
fi

# Initialize database
echo ""
echo "Initializing database..."
docker exec nocturne_backend python3 -c "from database import init_db; init_db()"
echo "✓ Database initialized"

# Check services
echo ""
echo "Checking services..."
echo ""

# Check backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ Backend is running: http://localhost:8000"
else
    echo "❌ Backend is not responding"
fi

# Check frontend
if curl -s http://localhost:5173 > /dev/null; then
    echo "✓ Frontend is running: http://localhost:5173"
else
    echo "❌ Frontend is not responding"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  - Frontend:    http://localhost:5173"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs:    http://localhost:8000/docs"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:5173 in your browser"
echo "  2. Select a city to view events"
echo "  3. Subscribe to email updates"
echo "  4. Click 'SCAN FOR UNDERGROUND' to refresh events"
echo ""
echo "Useful commands:"
echo "  - View logs:        docker-compose logs -f"
echo "  - Stop services:    docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Backend logs:     docker-compose logs -f backend"
echo "  - Frontend logs:    docker-compose logs -f frontend"
echo ""
echo "For testing, see TESTING_GUIDE.md"
echo "For documentation, see README.md"
echo ""
