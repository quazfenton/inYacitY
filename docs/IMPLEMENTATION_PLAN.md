# Full-Stack Integration Plan: Frontend + Backend

## Overview
This document outlines the plan to integrate the existing `fronto/` frontend with the `scraper/` backend to create a full-stack web application. The frontend will serve as the user interface while the backend handles event scraping, storage, and email subscriptions.

## Current Architecture Analysis

### Frontend (`fronto/`)
- Built with React + TypeScript + Vite
- Uses Tailwind CSS for styling
- Has mock data for NYC, Berlin, London, Tokyo, Los Angeles
- Includes city selector, event cards, subscribe form, vibe chart
- Has AI generation functionality (Gemini integration)
- Modern dark-themed UI with animations

### Backend (`scraper/`)
- Python-based event scraping system
- Supports Eventbrite, Meetup, and Luma
- Configurable by location (supports 40+ US cities)
- Stores events in JSON and markdown formats
- Has anti-detection measures for web scraping
- Runs as standalone scripts

## Goals
1. Integrate frontend with backend event data
2. Implement database storage for events
3. Add email subscription system
4. Create API layer to connect frontend and backend
5. Maintain all existing frontend aesthetics and functionality
6. Implement scheduled scraping via cron jobs

## Technical Implementation Plan

### Phase 1: Backend Infrastructure Setup

#### 1.1 Database Schema Design
- Create PostgreSQL database with tables:
  - `cities` table: city information (id, name, slug, coordinates)
  - `events` table: scraped events (title, location, date, time, description, tags, price, image_url, city_id, source, created_at)
  - `subscriptions` table: email subscriptions (email, city_id, created_at, active)

#### 1.2 API Layer Development
- Create FastAPI backend with endpoints:
  - `GET /api/cities` - List all available cities
  - `GET /api/events/{city_slug}` - Get events for specific city
  - `POST /api/subscribe` - Add email subscription
  - `GET /api/events/search` - Search events by criteria
  - `GET /api/stats/{city_slug}` - Get city statistics for vibe chart

#### 1.3 Data Migration
- Modify existing scraper scripts to save to database instead of files
- Create migration script to import existing JSON data to database
- Maintain backward compatibility with file-based storage during transition

### Phase 2: Backend Enhancement

#### 2.1 Scheduled Scraping System
- Implement cron job scheduler to run scrapers daily
- Create separate scrapers for each city in the config
- Add error handling and logging for scheduled tasks
- Implement rate limiting to avoid detection

#### 2.2 Email Subscription System
- Implement email validation and sanitization
- Create email template system for weekly updates
- Integrate with email sending service (SMTP/transactional email provider)
- Add unsubscribe functionality

#### 2.3 Security Enhancements
- Add input validation and sanitization
- Implement rate limiting for API endpoints
- Add authentication for admin functions
- Secure database connections with environment variables

### Phase 3: Frontend Integration

#### 3.1 API Integration
- Replace mock data with real API calls
- Update `CitySelector` component to fetch cities from API
- Update `EventCard` component to display real event data
- Connect `SubscribeForm` to subscription endpoint
- Update `VibeChart` to use real statistics

#### 3.2 State Management
- Implement Redux Toolkit or React Context for global state
- Manage loading states, error states, and data caching
- Add pagination for large event lists
- Implement offline-first approach with service workers

#### 3.3 UI/UX Improvements
- Maintain all existing animations and transitions
- Add loading indicators for API calls
- Implement infinite scrolling for event feeds
- Add search and filtering functionality
- Improve mobile responsiveness

### Phase 4: Deployment and Monitoring

#### 4.1 Infrastructure Setup
- Containerize application with Docker
- Set up CI/CD pipeline
- Deploy to cloud platform (AWS, GCP, or DigitalOcean)
- Configure SSL certificates and domain

#### 4.2 Monitoring and Logging
- Implement application monitoring
- Set up error tracking system
- Add performance metrics
- Create admin dashboard for monitoring

## Detailed Implementation Steps

### Step 1: Set Up Project Structure
```
project-root/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── database/
│   │   └── utils/
│   ├── requirements.txt
│   └── alembic/
├── frontend/         # React application (current fronto/)
├── scraper/          # Current scraper code (modified)
├── docker-compose.yml
└── README.md
```

### Step 2: Database Setup
1. Install PostgreSQL and create database
2. Define SQLAlchemy models matching event structure
3. Create Alembic migrations
4. Implement database connection pooling

### Step 3: API Development
1. Create FastAPI application
2. Implement CRUD operations for events and subscriptions
3. Add authentication middleware
4. Create API documentation with Swagger

### Step 4: Scraper Modification
1. Update scraper scripts to save to database
2. Create wrapper functions for each scraper type
3. Implement error handling and retry mechanisms
4. Add logging for debugging

### Step 5: Frontend Integration
1. Update API endpoints in service files
2. Replace mock data with real data
3. Add loading states and error handling
4. Implement search and filtering

### Step 6: Testing
1. Unit tests for API endpoints
2. Integration tests for scraper functionality
3. E2E tests for frontend flows
4. Performance testing for concurrent users

### Step 7: Deployment
1. Create Docker configuration
2. Set up production environment
3. Configure scheduled tasks
4. Monitor system performance

## Security Considerations

### Input Validation
- Validate all user inputs on both frontend and backend
- Sanitize email addresses and prevent injection attacks
- Implement proper error handling without exposing system details

### Authentication
- Implement JWT-based authentication for admin functions
- Secure API endpoints with proper authorization
- Add CSRF protection for forms

### Data Protection
- Encrypt sensitive data in database
- Implement secure password policies
- Regular security audits and updates

## Performance Optimization

### Database
- Add indexes for frequently queried fields
- Implement connection pooling
- Optimize queries for large datasets

### Caching
- Implement Redis for frequently accessed data
- Cache API responses appropriately
- Use CDN for static assets

### Frontend
- Code splitting and lazy loading
- Image optimization and compression
- Efficient state management

## Monitoring and Maintenance

### Logging
- Comprehensive logging for all system components
- Structured logging for easy analysis
- Log rotation and archival

### Error Tracking
- Real-time error monitoring
- Automated alerting for critical issues
- Performance metrics tracking

### Backup Strategy
- Regular database backups
- Version control for all code
- Disaster recovery plan

## Timeline Estimation

- Phase 1 (Backend Infrastructure): 1-2 weeks
- Phase 2 (Backend Enhancement): 1-2 weeks  
- Phase 3 (Frontend Integration): 1-2 weeks
- Phase 4 (Deployment and Monitoring): 1 week
- Testing and Bug Fixes: 1 week

**Total Estimated Time: 5-8 weeks**

## Risk Mitigation

### Technical Risks
- Anti-bot measures from event platforms: Implement rotating proxies and realistic delays
- Data inconsistency: Implement data validation and cleaning processes
- Scalability issues: Design for horizontal scaling from the start

### Operational Risks
- Email deliverability: Use reputable email service providers
- Downtime: Implement redundancy and monitoring
- Legal compliance: Ensure compliance with terms of service and privacy laws

## Success Metrics

- Number of active subscribers
- Daily/monthly active users
- Email open rates and engagement
- System uptime and performance
- Successful event scrapes per day
- User satisfaction scores

## Future Enhancements

- Mobile app development
- Advanced recommendation algorithms
- Social features and user profiles
- Integration with calendar applications
- Push notifications
- Advanced analytics dashboard