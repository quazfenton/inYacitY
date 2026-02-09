---
description: Repository Information Overview
alwaysApply: true
---

# Nocturne Event Platform Information

## Repository Summary
Nocturne is an event discovery platform designed for "underground" event discovery. It features a multi-component architecture including a FastAPI backend, a React-based frontend, and a specialized web scraper for various event platforms.

## Repository Structure
- **backend/**: FastAPI-based REST API handling event management, user subscriptions, and integration with the scraper and database.
- **fronto/**: Modern React frontend built with Vite, TypeScript, and Tailwind CSS.
- **scraper/**: Specialized Python scrapers using Playwright and BeautifulSoup to extract event data from platforms like Eventbrite, Dice, and Meetup.
- **n8n/**: Workflow automation configurations for scheduled scraping tasks.
- **scripts/**: Utility scripts for project setup and environment configuration.

## Projects

### Backend (API)
**Configuration File**: [./backend/main.py](./backend/main.py), [./backend/requirements.txt](./backend/requirements.txt)

#### Language & Runtime
**Language**: Python  
**Version**: 3.11  
**Build System**: pip  
**Package Manager**: pip

#### Dependencies
**Main Dependencies**:
- **fastapi**: Web framework
- **sqlalchemy**: ORM for database management
- **psycopg2-binary**: PostgreSQL adapter
- **pydantic**: Data validation
- **pyjwt**: JWT authentication
- **gunicorn**: Production WSGI/ASGI server

**Development Dependencies**:
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting

#### Build & Installation
```bash
cd backend
pip install -r requirements.txt
```

#### Docker
**Dockerfile**: [./backend/Dockerfile](./backend/Dockerfile)
**Configuration**: Uses `python:3.11-slim` base image, installs system dependencies for PostgreSQL and Playwright, and runs with Gunicorn and Uvicorn workers.

#### Testing
**Framework**: pytest
**Test Location**: [./backend/tests/](./backend/tests/) (Expected location)
**Run Command**:
```bash
pytest backend/
```

### Frontend (User Interface)
**Configuration File**: [./fronto/package.json](./fronto/package.json)

#### Language & Runtime
**Language**: TypeScript / React  
**Version**: Node.js 20  
**Build System**: Vite  
**Package Manager**: npm

#### Dependencies
**Main Dependencies**:
- **react**: UI library
- **axios**: HTTP client
- **lucide-react**: Icon library
- **recharts**: Data visualization

#### Build & Installation
```bash
cd fronto
npm install
npm run build
```

#### Docker
**Dockerfile**: [./fronto/Dockerfile](./fronto/Dockerfile)
**Configuration**: Uses `node:20-alpine`, builds the production assets, and serves them using the `serve` utility.

### Scraper (Data Extraction)
**Configuration File**: [./scraper/requirements.txt](./scraper/requirements.txt)

#### Language & Runtime
**Language**: Python  
**Package Manager**: pip

#### Key Resources
**Main Files**:
- [./scraper/run.py](./scraper/run.py): Main scraper orchestration script.
- [./scraper/eventbrite_scraper.py](./scraper/eventbrite_scraper.py): Platform-specific scraper.
- [./scraper/dice_scraper.py](./scraper/dice_scraper.py): Platform-specific scraper.

#### Usage & Operations
**Key Commands**:
```bash
python scraper/run.py
```

#### Testing
**Framework**: Manual scripts and specialized test files.
**Test Location**: [./scraper/test_scrapers.py](./scraper/test_scrapers.py)
**Run Command**:
```bash
python scraper/test_scrapers.py
```

## Infrastructure & Deployment
**Orchestration**: Docker Compose
**Main Services**:
- **postgres**: Database service using `postgres:15-alpine`.
- **backend**: API service on port 8000.
- **frontend**: Web UI service on port 5173.

**Deployment Command**:
```bash
docker-compose up -d
```
