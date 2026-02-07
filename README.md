# Nocturne Event Platform

## Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Git

### Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd inyAcity
```

2. Copy the example environment file and configure your credentials:
```bash
cp .env.example .env
```

3. Edit the `.env` file to set your database credentials and other configurations:
```bash
nano .env
```

4. Start the services:
```bash
docker-compose up -d
```

## Environment Variables

The application uses environment variables for configuration. Copy `.env.example` to `.env` and customize the values:

- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `DATABASE_URL`: Full database connection string
- `ALLOWED_ORIGINS`: Allowed origins for CORS
- `SMTP_*`: Email configuration variables
- `SENDGRID_*`: SendGrid configuration variables
- `VITE_API_URL`: Frontend API URL
- `JWT_SECRET_KEY`: Secret key for JWT token signing (default: "your-super-secret-key-change-in-production")
- `ADMIN_API_KEY`: API key for admin authentication

**Important**: Do not commit your `.env` file to version control. The `.env` file is already added to `.gitignore`.

## Services

- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- Database: localhost:5432

## Admin Authentication

Some endpoints require admin authentication. To access admin endpoints:

1. Set the `ADMIN_API_KEY` in your `.env` file
2. Generate an admin JWT token by calling the `/admin/login` endpoint with your API key:
   ```bash
   curl -X POST http://localhost:8000/admin/login \
     -H "Content-Type: application/json" \
     -d '{"api_key": "your-admin-api-key"}'
   ```
3. Use the returned JWT token in the Authorization header for admin endpoints:
   ```bash
   curl -X GET http://localhost:8000/subscriptions \
     -H "Authorization: Bearer your-jwt-token-here"
   ```

## Development

To rebuild containers after changes:
```bash
docker-compose build
docker-compose up -d
```

To view logs:
```bash
docker-compose logs -f
```

## Stopping Services

```bash
docker-compose down
```