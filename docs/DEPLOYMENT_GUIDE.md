# Deployment Guide for Nocturne Platform

This guide covers deploying Nocturne to production environments including VPS, cloud providers, and containerized deployments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Option 1: Docker Compose (VPS)](#option-1-docker-compose-vps)
4. [Option 2: Kubernetes](#option-2-kubernetes)
5. [Option 3: Cloud Platforms](#option-3-cloud-platforms)
6. [Database Setup](#database-setup)
7. [SSL/HTTPS Setup](#sslhttps-setup)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup Strategy](#backup-strategy)
10. [Security Hardening](#security-hardening)
11. [Performance Optimization](#performance-optimization)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:

- ✅ Domain name (e.g., `nocturne.events`)
- ✅ Server or cloud account with:
  - At least 2GB RAM
  - 20GB storage
  - 2 CPU cores
- ✅ Docker and Docker Compose installed (for VPS deployment)
- ✅ SSL certificate (Let's Encrypt recommended)
- ✅ Production database (PostgreSQL 15+)
- ✅ Email service configured (SMTP or SendGrid)
- ✅ Environment variables prepared

## Deployment Options

### Comparison

| Option | Complexity | Cost | Scalability | Best For |
|--------|------------|------|-------------|-----------|
| Docker Compose | Low | $5-20/mo | Medium | Small to medium apps |
| Kubernetes | High | $50-200/mo | High | Large, complex apps |
| Cloud Platform | Medium | $20-100/mo | High | Rapid deployment |
| Serverless | Medium | Pay-per-use | High | Variable traffic |

## Option 1: Docker Compose (VPS)

### 1.1 Server Setup

**Recommended VPS Providers:**
- DigitalOcean Droplets
- Linode
- AWS EC2 (t3.medium)
- Google Cloud Compute Engine (e2-medium)
- Vultr
- Hetzner

**Initial Server Setup (Ubuntu 22.04):**

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 1.2 Clone Repository

```bash
# Clone repository (replace with your repository URL)
git clone https://github.com/your-username/inyAcity.git
cd inyAcity
```

### 1.3 Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit with production values
nano .env
```

**Production .env example:**

```bash
# Database (use managed PostgreSQL if possible)
DATABASE_URL=postgresql+asyncpg://nocturne:STRONG_PASSWORD@managed-db-host:5432/nocturne

# Frontend (set production domain)
VITE_API_URL=https://api.nocturne.events

# Email (SendGrid recommended for production)
SENDGRID_API_KEY=SG.your-production-key
SENDGRID_FROM_EMAIL=noreply@nocturne.events

# Optional: Scraper fallback APIs
FIRECRAWL_API_KEY=your-key
HYPERBROWSER_API_KEY=your-key
```

### 1.4 Update docker-compose.yml for Production

```bash
nano docker-compose.yml
```

**Production modifications:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: nocturne_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: nocturne
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: nocturne
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - nocturne_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nocturne"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nocturne_backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # Only accessible via reverse proxy
    environment:
      DATABASE_URL: postgresql+asyncpg://nocturne:${DB_PASSWORD}@postgres:5432/nocturne
      VITE_API_URL: https://api.nocturne.events
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - nocturne_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./fronto
      dockerfile: Dockerfile
    container_name: nocturne_frontend
    restart: unless-stopped
    ports:
      - "80:80"  # Will be proxied by nginx
    environment:
      VITE_API_URL: https://api.nocturne.events
    depends_on:
      - backend
    networks:
      - nocturne_network

  nginx:
    image: nginx:alpine
    container_name: nocturne_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - nocturne_network

volumes:
  postgres_data:

networks:
  nocturne_network:
    driver: bridge
```

### 1.5 Create Nginx Configuration

```bash
mkdir ssl
nano nginx.conf
```

**nginx.conf:**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name nocturne.events api.nocturne.events;
        
        # Let's Encrypt challenge
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name nocturne.events;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # HTTPS API server
    server {
        listen 443 ssl http2;
        server_name api.nocturne.events;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # API endpoints with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            # CORS headers
            add_header 'Access-Control-Allow-Origin' 'https://nocturne.events' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
            
            if ($request_method = 'OPTIONS') {
                return 204;
            }
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 1.6 Obtain SSL Certificate

**Using Certbot:**

```bash
# Install certbot
apt install certbot -y

# Obtain certificate (standalone mode, temporarily stop nginx)
docker-compose stop nginx

certbot certonly --standalone -d nocturne.events -d api.nocturne.events --email your-email@example.com --agree-tos --non-interactive

# Copy certificates to project
cp /etc/letsencrypt/live/nocturne.events/fullchain.pem ./ssl/
cp /etc/letsencrypt/live/nocturne.events/privkey.pem ./ssl/

# Set up auto-renewal
echo "*/5 * * * * certbot renew --quiet && docker-compose restart nginx" | crontab -

# Start nginx
docker-compose up -d nginx
```

### 1.7 Deploy Application

```bash
# Build and start services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 1.8 Configure DNS

**DNS Records:**
```
Type    Name                Value
A       @                   your-server-ip
A       api                 your-server-ip
AAAA    @                   your-ipv6-address (optional)
```

### 1.9 Initial Data Load

```bash
# Scrape events for all cities
docker-compose exec backend python3 -c "
from scraper_integration import refresh_all_cities
import asyncio
asyncio.run(refresh_all_cities())
"

# Set up cron job for daily scraping
echo "0 2 * * * cd /root/inyAcity && docker-compose exec backend python3 cron_scraper.py daily" | crontab -

# Verify cron job
crontab -l
```

### 1.10 Monitor Deployment

```bash
# Check service health
curl https://api.nocturne.events/health

# Check frontend
curl https://nocturne.events

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Option 2: Kubernetes

### 2.1 Prerequisites

- Kubernetes cluster (GKE, EKS, AKS, or local minikube/k3s)
- kubectl configured
- Helm installed
- Persistent storage (for PostgreSQL)

### 2.2 Create Kubernetes Secrets

```bash
kubectl create secret generic nocturne-secrets \
  --from-literal=database-url="postgresql+asyncpg://user:pass@host/db" \
  --from-literal=sendgrid-api-key="SG.your-key" \
  --from-literal=vite-api-url="https://api.nocturne.events"
```

### 2.3 Deploy PostgreSQL

**Create postgres-deployment.yaml:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          value: nocturne
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: nocturne-secrets
              key: db-password
        - name: POSTGRES_DB
          value: nocturne
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

**Deploy:**
```bash
kubectl apply -f postgres-deployment.yaml
```

### 2.4 Deploy Backend

**Create backend-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: nocturne/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: nocturne-secrets
              key: database-url
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

**Deploy:**
```bash
kubectl apply -f backend-deployment.yaml
```

### 2.5 Deploy Frontend

**Create frontend-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: nocturne/frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: VITE_API_URL
          valueFrom:
            secretKeyRef:
              name: nocturne-secrets
              key: vite-api-url
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**Deploy:**
```bash
kubectl apply -f frontend-deployment.yaml
```

### 2.6 Ingress Configuration

**Create ingress.yaml:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nocturne-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - nocturne.events
    - api.nocturne.events
    secretName: nocturne-tls
  rules:
  - host: nocturne.events
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  - host: api.nocturne.events
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
```

**Deploy:**
```bash
kubectl apply -f ingress.yaml
```

## Option 3: Cloud Platforms

### 3.1 Render (Recommended)

Render provides a simple PaaS experience with free tiers.

**Steps:**

1. **Push code to GitHub**

2. **Create PostgreSQL service:**
   - Go to Render Dashboard
   - New → PostgreSQL
   - Name: `nocturne-db`
   - Choose instance size (Free tier for testing)
   - Copy internal connection string

3. **Create Backend service:**
   - New → Web Service
   - Connect GitHub repository
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables:
     - `DATABASE_URL`: (from PostgreSQL service)
     - `SENDGRID_API_KEY`: your key
     - `VITE_API_URL`: your backend URL

4. **Create Frontend service:**
   - New → Static Site
   - Connect GitHub repository
   - Root directory: `fronto`
   - Build command: `npm run build`
   - Publish directory: `dist`
   - Add environment variable:
     - `VITE_API_URL`: your backend URL

5. **Create cron jobs:**
   - New → Cron Job
   - Command: `python3 cron_scraper.py daily`
   - Schedule: `0 2 * * *`

### 3.2 Railway

1. **Create project**
2. **Add PostgreSQL service**
3. **Add backend service** with:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Add frontend service** with:
   - Build: `npm install && npm run build`
   - Start: `npm run preview`

### 3.3 Heroku

**Create Procfile for backend:**

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Create Procfile for frontend:**

```
web: npm run preview
```

**Deploy:**
```bash
# Backend
heroku create nocturne-backend --buildpack heroku/python
heroku addons:create heroku-postgresql
heroku config:set DATABASE_URL=...
git push heroku main

# Frontend
heroku create nocturne-frontend --buildpack heroku/nodejs
heroku config:set VITE_API_URL=https://nocturne-backend.herokuapp.com
git push heroku main
```

## Database Setup

### Managed PostgreSQL Options

**Recommended providers:**

1. **AWS RDS** - Starting at $15/mo
2. **Google Cloud SQL** - Starting at $10/mo
3. **DigitalOcean Managed DB** - Starting at $15/mo
4. **Railway** - Starting at $5/mo
5. **Neon** - Serverless, $0.20/GB storage

**Connection String Format:**
```
postgresql+asyncpg://user:password@host:port/database
```

### Database Backups

**Automated backups:**

```bash
# Add to crontab for daily backups
0 3 * * * pg_dump -h localhost -U nocturne nocturne | gzip > /backups/nocturne_$(date +\%Y\%m\%d).sql.gz
```

**Restoring from backup:**
```bash
gunzip < backup_file.sql.gz | psql -h localhost -U nocturne nocturne
```

## SSL/HTTPS Setup

### Option 1: Let's Encrypt (Free)

**Certbot with Nginx:**

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Obtain certificate
certbot --nginx -d nocturne.events -d api.nocturne.events

# Auto-renewal is configured automatically
certbot renew --dry-run
```

### Option 2: Cloudflare SSL

1. **Set Cloudflare nameservers for your domain**
2. **Enable "Full" SSL/TLS mode**
3. **Create origin certificates** in Cloudflare dashboard
4. **Upload certificates to nginx**

### Option 3: AWS Certificate Manager

```bash
# Using AWS CLI
aws acm request-certificate \
  --domain-name nocturne.events \
  --subject-alternative-names api.nocturne.events \
  --validation-method DNS
```

## Monitoring & Logging

### Application Monitoring

**Prometheus + Grafana:**

```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  volumes:
    - grafana_data:/var/lib/grafana
```

**Key metrics to monitor:**
- API response times
- Error rates
- Database query performance
- CPU/memory usage
- Event count per city

### Logging

**Structured logging:**

```python
# Add to backend/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@app.get("/events/{city_id}")
async def get_city_events(city_id: str, db=Depends(get_db)):
    logger.info(f"Fetching events for city: {city_id}")
    # ... rest of endpoint
```

**Log aggregation options:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana (lighter alternative)
- CloudWatch Logs (AWS)
- Stackdriver (GCP)

## Backup Strategy

### Daily Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d)
DB_NAME="nocturne"

# Database backup
pg_dump -h localhost -U nocturne $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/db_$DATE.sql.gz s3://nocturne-backups/
```

**Add to crontab:**
```bash
0 3 * * * /root/backup.sh
```

### Disaster Recovery Plan

1. **Database**: Daily backups + point-in-time recovery
2. **Application code**: Version control (Git)
3. **Configuration**: Version control + secrets management
4. **Static assets**: CDN backup

## Security Hardening

### 1. Network Security

```yaml
# Only allow necessary ports in firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny all
ufw enable
```

### 2. Application Security

**Update backend CORS:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nocturne.events"],  # Specific domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
```

**Add rate limiting:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/subscribe")
@limiter.limit("5/minute")  # 5 subscriptions per minute per IP
async def subscribe(subscription: SubscriptionCreate):
    # ...
```

### 3. Secrets Management

**Use environment variables:**
- Never commit `.env` to git
- Use `python-dotenv` for loading
- Use HashiCorp Vault for production

### 4. Regular Updates

```bash
# Keep system updated
apt update && apt upgrade -y

# Keep Docker images updated
docker-compose pull
docker-compose up -d

# Keep dependencies updated
cd backend
pip install --upgrade -r requirements.txt
```

## Performance Optimization

### 1. Database Optimization

**Add indexes:**

```sql
-- Already in schema, but verify
CREATE INDEX IF NOT EXISTS idx_events_city_date ON events(city_id, date);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(city_id, is_active);
```

**Connection pooling:**
```python
# Already configured in database.py
pool_size=10,
max_overflow=20
```

### 2. Caching

**Add Redis cache:**

```yaml
# Add to docker-compose.yml
redis:
  image: redis:alpine
  ports:
    - "6379:6379"
```

**Implement caching in API:**

```python
import aioredis

redis = aioredis.from_url("redis://redis:6379")

@app.get("/events/{city_id}")
async def get_city_events(city_id: str, db=Depends(get_db)):
    # Check cache first
    cached = await redis.get(f"events:{city_id}")
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    events = await fetch_events(city_id, db)
    
    # Cache for 5 minutes
    await redis.setex(f"events:{city_id}", 300, json.dumps(events))
    
    return events
```

### 3. CDN for Static Assets

**Serve static assets via CDN:**

```yaml
# nginx.conf
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    proxy_pass https://cdn.nocturne.events;
}
```

## Troubleshooting

### Issue: Container won't start

```bash
# Check logs
docker-compose logs backend

# Check resource usage
docker stats

# Restart service
docker-compose restart backend
```

### Issue: Database connection failed

```bash
# Test database connection
docker exec -it postgres psql -U nocturne -d nocturne -c "SELECT 1"

# Check environment variables
docker-compose exec backend env | grep DATABASE_URL

# Verify network
docker network inspect inyacity_nocturne_network
```

### Issue: SSL certificate error

```bash
# Check certificate validity
openssl x509 -in ssl/fullchain.pem -text -noout

# Renew certificate
certbot renew

# Reload nginx
docker-compose restart nginx
```

### Issue: High CPU usage

```bash
# Check which process is using CPU
docker exec backend top

# Check database queries
docker exec postgres psql -U nocturne -d nocturne -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
"
```

### Issue: Disk space full

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a --volumes

# Clean up old logs
find /var/log -name "*.log" -mtime +30 -delete

# Clean up old backups
find /backups -name "db_*.sql.gz" -mtime +30 -delete
```

## Post-Deployment Checklist

- [ ] Application accessible at domain
- [ ] SSL certificate valid
- [ ] Database connection working
- [ ] API endpoints responding
- [ ] Email service configured
- [ ] Daily scraping cron job set up
- [ ] Monitoring configured
- [ ] Backups running
- [ ] SSL auto-renewal configured
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] CORS configured correctly
- [ ] Error logging set up
- [ ] Health checks passing

## Conclusion

You now have a fully deployed Nocturne platform. For ongoing maintenance:

- Monitor logs daily
- Check metrics weekly
- Update dependencies monthly
- Review security quarterly
- Test backup restoration periodically

For additional support, consult the [TESTING_GUIDE.md](TESTING_GUIDE.md) and [README.md](README.md).
