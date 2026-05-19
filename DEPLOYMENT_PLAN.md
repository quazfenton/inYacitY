# Nocturne Deployment Plan — Multi-Cloud Strategy

## Project Architecture Recap

| Layer | Tech | Details |
|---|---|---|
| Frontend | React 19 / Vite 6 / TS | SPA, city selector, event feed, RSVP, comments |
| Backend | FastAPI / Python 3.11 | 20+ REST endpoints, auth, email, scraping bridge |
| Database | PostgreSQL 15 | Events, subscriptions, email logs, RSVP, comments |
| Shared Cache | Supabase PostgreSQL | Multi-user event sharing (optional sync layer) |
| Scraper | Python / Playwright | 6 sources, 51 cities, eventbrite/meetup/luma/dice/RA/posh |
| Automation | n8n | Daily cron scraping, weekly digest, cleanup |
| Proxy | Nginx | Reverse proxy `/api/*` → backend, `/` → frontend |

---

## Component → Platform Mapping

### 1. FRONTEND → **Vercel** (static)

```
Component  : React 19 + Vite 6 SPA
Platform   : Vercel Free Tier
Why        : Zero-config React/Vite deploy, automatic CDN edge delivery,
             preview branches on PRs, built-in image optimization, env vars.
Build cmd  : npm run build
Output     : dist/
Env vars   : VITE_API_BASE_URL=<backend-url>
            NEXT_PUBLIC_SUPABASE_URL=... (if used)
```

**Vercel config (`vercel.json`):**
```json
{ "buildCommand": "npm run build", "outputDirectory": "dist", "rewrites": [{ "source": "/api/(.*)", "destination": "https://api.nocturne.workers.sh/$1" }] }
```

The frontend calls `/api/*`, `/api/locations/*`. In production route these through the FastAPI backend (Oracle/VPS or Railway/Render). The frontend's `API_BASE_URL` in `fronto/constants.ts` needs to point at whichever host the backend is deployed to.

---

### 2. API / BACKEND → **Oracle Cloud Free Tier** (Compute VM)

```
Component  : FastAPI + Flask + Scraper Bridge + Email + Auth
Platform   : Oracle Cloud Infrastructure (OCI) Always Free VM.Standard.E2.1.Micro
             — 4 ARM Ampere A1 cores @ 24GB RAM or x86 VM plan
Why        : Unlimited compute / outbound bandwidth, full root access on a Linux VM,
              24GB RAM for 4 cores is well above the FastAPI + Postgres + Redis needs.
              Playwright browser installs natively with apt + pip.
              N8N can run on same VM as a systemd service.
              
Resources per VM :
  - 4 x OCPU, 24 GB RAM
  - 2 x 200 GB block volumes total
  - 10 TB outbound data per month
```

**Deploy to Oracle as systemd services:**

| Service | Port | User | Proxy |
|---|---|---|---|
| `postgresql` | 5432 | postgres | systemd |
| `nocturne-api` (gunicorn+uvicorn) | 8000 | nocturne | systemd |
| `n8n` | 5678 | n8n | systemd + nginx |

All routed via local nginx:
```
80/443  →  /          →  Vercel (static — optional, or direct Vercel)
         →  /api/*    →  http://127.0.0.1:8000
         →  /health   →  http://127.0.0.1:8000/health
         →  /n8n      →  http://127.0.0.1:5678
```

**Reasoning:**
- Free tier has the highest resource ceiling for hairy Playwright scrapers and gunicorn workers
- Full `apt-get install` for browser automation runtime
- PostgreSQL on the same VM = no data egress costs for DB reads
- n8n is a long-running process — best on always-on VM
- Avoid a microservice split for the scraping layer (6 sources × 51 cities = heavy async I/O; one worker pool is simpler)

---

### 3. PRIMARY DATABASE → **Supabase** (cloud Postgres)

```
Component  : Supabase PostgreSQL
             — events, subscriptions, email_logs, comments, RSVPs
Platform   : Supabase Free Tier
Why        : The project was built with Supabase integration at its core.
              Auto-bases per-plan limits are sufficient for event data volume
             at free scale. Free tier includes 500 MB database space, 50,000
             monthly active users, and 1 GB file storage.
             
Tables      : events_public, subscriptions, email_logs, comments, rsvps
Region      : Closest to your users
Auth        : Supabase Auth if you later want user accounts
Row limits  : 500 MB — paginate events or prune past events to stay within it
```

**Fallback (if Supabase free tier runs out of space):**
- Supabase `events` table is read-through cache. All scraped events are also saved in
  the Oracle-side Postgres at all times. Supabase is a lightweight sync layer for
  multi-user realtime, not the authoritative source. You can disable the Supabase sync
  by removing the `SUPABASE_URL` and `SUPABASE_KEY` env vars from the backend and the
  app degrades gracefully to the local Oracle Postgres.

---

### 4. SCRAPER → **Oracle VM** (as systemd cron job)

```
Component  : Python scraper (run.py master orchestrator)
Platform   : Oracle Cloud Free Tier (same VM as backend)
Why        : Playwright needs an actual kernel / X libs for browser automation.
              The cloud VM has no headless-Browser restrictions.
              
Execution  : Automated via systemd timer (or cron) every 4–6 hours:
  /opt/nocturne/scraper/run.py
  → writes all_events.json
  → uploads to Supabase via supabase_integration
  → sends events to PostgreSQL

Cron setup :
  0 */6 * * * cd /opt/nocturne && /usr/bin/python3 scraper/run.py >> /var/log/nocturne/scraper.log 2>&1
```

---

### 5. AUTOMATION (n8n) → **Oracle VM** (systemd service)

```
Component  : n8n workflow engine
Platform   : Oracle Cloud Free Tier (same VM as backend)
Port       : 5678 (proxied via nginx as needed)
Creds      : Set N8N_ENCRYPTION_KEY, SUPABASE_URL, SUPABASE_KEY
Why        : n8n is what manages the daily scrape cron and weekly digest emails.
              Orchestration state lives in Postgres (you can use the same Oracle Postgres
              or its own on port 5433 as in docker-compose.n8n.yml).
Remaining free tier limits (n8n cloud free):
  — Workflow executions: 100/mo (free cloud tier)
  — For unlimited no-limit: self-hosting on Oracle VM as above
  n8n is already included AND self-hostable in vm with the full OCI 10TB outbandwidth
```

**n8n is deployed to the Oracle VM in this plan.**

---

### 6. CACHING / GEO LOCATION / RATE LIMITING → **Render Free Web Service** or **Oracle Redis**

```
Component  : Redis (rate limiting, scraper cache, optional geolocation cache)
Option A   : Oracle VM — install redis-server on same VM
             (simpler, zero-latency, no data egress cost)
Option B   : Render Free Redis 
             (if you prefer separate service; 256 MB RAM — watch usage)

Recommendation: For the free scale, install Redis on the Oracle VM:
  apt install redis-server
  systemctl enable --now redis
```

---

### 7. QA / CI — **GitHub Actions + Qodana**

```
Component  : Static analysis, lint, type check
Platform   : Qodana Cloud Free + GitHub Actions
Purpose    : Pre-merge code quality gate
Triggers   : On push to main, on PR label "autofix", nightly scheduled
Workflows  : Already have jarvis.yml for aider fixes
Add Qodana: .github/workflows/qodana.yml
           — Runs Qodana on Python backend + TypeScript frontend
           — Reports violations as PR annotations
```

**Qodana and CNAME setup for Public CI PR and Branch Report is auto managed by qodana cloud**

---

## Full Deployment Topology

```
 ┌──────────────────────────────────────────────────────────────────┐
 │  INTERNET                                                         │
 └──────────┬───────────────────────────┬────────────────────────────┘
            │                           │
    ┌───────▼────────┐          ┌───────▼────────┐
    │  Vercel Edge   │          │   Oracle VM    │
    │  (React SPA)   │          │  (Always Free) │
    │  fronto/* CDN  │          │                │
    └───────┬────────┘          │  ┌──────────┐  │
            │ /api/* calls       │  │Nginx 80  │  │
            ▼                    │  └────┬─────┘  │          
 ┌──────────────────┐            │       │        │
 │  Railway / Render │            │       │        │
 │  FastAPI staging │            │       ▼        │
 │  (pre-production)│            │  ┌──────────┐  │
 └──────────────────┘            │  │  port    │──┼──► http://127.0.0.1:8000
                                  │  │  8000    │  │   (Gunicorn + Uvicorn ×4)
                                  │  │ API Svc  │  │
                                  │  └────┬─────┘  │
                                  │       │        │
                         ┌────────┘  ┌───▼─────┐   │
                         │          │ Postgres│   │
                         │          │ 5432    │   │
                         │          └───┬─────┘   │
                         │              │ Authori- │
                         │        ┌─────▼─────┐   │
                         │        │ Supabase  │   │
                         │        │ Free Tier │◄──┘◄── sync layer
                         │        │ (shared   │
                         │        │   cache)  │
                         │        └───────────┘
                         │
                  ┌──────▼──────┐
                  │    n8n       │
                  │   (port      │
                  │   5678)      │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │  (optional)   │
                  │Scaleway/Object│
                  │Storage /      │
                  │static assets  │
                  └──────────────┘
```

---

## Environment Variables (Orchestration)

| Variable | Where set | Notes |
|---|---|---|
| `DATABASE_URL` | Oracle VM `.env` + systemd service file | `postgresql+asyncpg://user:pass@localhost:5432/nocturne` |
| `SUPABASE_URL` | Oracle VM + Vercel | Supabase project URL |
| `SUPABASE_KEY` | Oracle VM + Vercel (anon key only) | Never expose service_role key to frontend |
| `JWT_SECRET` | Oracle VM | 32+ random chars |
| `ADMIN_API_KEY` | Oracle VM | Arbitrary long token |
| `SMTP_*` | Oracle VM | SMTP + SendGrid credentials |
| `N8N_ENCRYPTION_KEY` | Oracle VM | n8n internals encryption key |
| `VITE_API_BASE_URL` | Vercel (preview + prod) | `https://api.nocturne.workers.sh` or Oracle IP/domain |
| `VITE_SUPABASE_URL` | Vercel | Frontend Supabase client init |
| `VITE_SUPABASE_ANON_KEY` | Vercel | Supabase frontend key |

---

## Deployment Phases

### Phase 1 — Oracle VM Bootstrap (Day 1)

```bash
# 1. Spin up Oracle Always Free VM (ARM Ampere recommended for best free tier)
# 2. SSH into VM as opc
ssh opc@<oracle-ip>

# 3. Provision system packages
sudo apt update && sudo apt install -y \
  python3 python3-venv python3-pip \
  nginx postgresql postgresql-contrib postgresql-client \
  redis-server certbot python3-certbot-nginx \
  git curl

# 4. Clone repo
git clone https://github.com/<repo>/inYacitY.git /opt/nocturne
cd /opt/nocturne

# 5. Python env
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 6. PostgreSQL setup
sudo -u postgres createuser nocturne
sudo -u postgres createdb -O nocturne nocturne
sudo -u postgres psql -c "ALTER USER nocturne WITH PASSWORD '<secure-pass>';"

# 7. Init DB tables
python backend/migrations.py

# 8. FastAPI systemd service
sudo tee /etc/systemd/system/nocturne-api.service > /dev/null <<'EOF'
[Unit]
Description=Nocturne FastAPI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=nocturne
Group=nocturne
Environment="DATABASE_URL=postgresql+asyncpg://nocturne:<pass>@localhost:5432/nocturne"
Environment="SUPABASE_URL=<url>"
Environment="SUPABASE_KEY=<key>"
Environment="JWT_SECRET=<jwt>"
Environment="ADMIN_API_KEY=<api-key>"
Environment="SMTP_*..."
WorkingDirectory=/opt/nocturne/backend
ExecStart=/opt/nocturne/venv/bin/gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nocturne-api
sudo systemctl status nocturne-api
```

### Phase 2 — Nginx + SSL (Day 1)

```nginx
# /etc/nginx/sites-available/nocturne
server {
  listen 80;
  server_name api.nocturne.com;

  access_log /var/log/nginx/nocturne-api.access.log;
  error_log  /var/log/nginx/nocturne-api.error.log;

  location /api/  { proxy_pass http://127.0.0.1:8000/;   include proxy_params; }
  location /health { proxy_pass http://127.0.0.1:8000/health; include proxy_params; }
  location /admin  { proxy_pass http://127.0.0.1:8000/admin;  include proxy_params; }

  client_max_body_size 50M;
}

server {
  listen 80;
  server_name www.nocturne.com noocturne.com;  # frontend (Vercel-managed, CNAME only)
}
```

```bash
# SSL
sudo certbot --nginx -d api.nocturne.com
```

### Phase 3 — Supabase Project (Day 1)

1. Create Supabase project `nocturne-prod` (or `staging` first)
2. Run SQL schema (see `SUPABASE_SETUP.md` for exact CREATE TABLE scripts):
   - `events`, `subscriptions`, `email_logs`, `comments`, `rsvps`
3. Enable RLS policies
4. Get `anon` key — set on Oracle VM env + Vercel env vars
5. Test: `curl -H "Authorization: Bearer <anon>" https://<project>.supabase.co/rest/v1/events?limit=0`

### Phase 4 — n8n on Oracle VM (Day 2)

```bash
# Install n8n globally
sudo npm install -g n8n

# Or use Docker Compose from existing docker-compose.n8n.yml
cd /opt/nocturne
docker compose -f docker-compose.n8n.yml up -d

# Set env vars for n8n
N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
N8N_PROTOCOL=https
N8N_HOST=n8n.nocturnne.com   # proxy via nginx
SUPABASE_URL=<project-url>
SUPABASE_KEY=<anon-key>

# Import workflow
n8n import:workflow --file=n8n/nocturne-daily-scraper.json
# Connect daily-scrape webhook → curl POST localhost:8000/api/scrape/all
# Connect weekly-digest → python backend/weekly_digest.py --send
```

### Phase 5 — Scraper Scaled Cron (Day 2)

```bash
# systemd timer for every 6 hours
sudo tee /etc/systemd/system/nocturne-scraper.timer > /dev/null <<'EOF'
[Unit]
Description=Run Nocturne scraper every 6 hours

[Timer]
OnBootSec=15min
OnUnitActiveSec=6h

[Install]
WantedBy=timers.target
EOF

sudo tee /etc/systemd/system/nocturne-scraper.service > /dev/null <<'EOF'
[Unit]
Description=Nocturne Scraper
After=network.target

[Service]
Type=oneshot
User=nocturne
WorkingDirectory=/opt/nocturne
Environment="SUPABASE_URL=<url>"
Environment="SUPABASE_KEY=<key>"
Environment="SUPABASE_ANON_KEY=<anon>"
ExecStart=/opt/nocturne/venv/bin/python scraper/run.py
StandardOutput=append:/var/log/nocturne/scraper.log
StandardError=append:/var/log/nocturne/scraper.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nocturne-scraper.timer
```

### Phase 6 — Frontend Deployment to Vercel (Day 3)

```bash
cd fronto

# Create vercel.json
cat > vercel.json << 'EOF'
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "framework": "vite",
  "env": {
    "VITE_API_BASE_URL": "https://api.nocturne.com",
    "VITE_SUPABASE_URL": "@supabase_url",
    "VITE_SUPABASE_ANON_KEY": "@supabase_anon_key"
  }
}
EOF

# Deploy
vercel --prod --token $VERCEL_TOKEN
```

Set Vercel environment variables in Vercel dashboard:
- `VITE_API_BASE_URL` → `https://api.nocturne.com`
- `VITE_SUPABASE_URL` → Supabase project URL
- `VITE_SUPABASE_ANON_KEY` → Supabase anon key

---

## Platform Rationale Summary

| Layer | Platform | Why Not Others |
|---|---|---|
| **Frontend** | **Vercel** | Best Vite/React DX, automatic CDN, preview deploys |
| **Backend API** | **Oracle Free VM** | Unlimited compute bandwidth, can install Playwright/pip deps, full OS control. Render/Railway/Vercel Functions — all have function execution limits (10s cold start, memory caps). |
| **Primary DB** | **Supabase** | Built-in realtime for multi-user caching, postgres-level security and backups, built-in table view |
| **Scraper** | **Oracle VM** (on same host as API) | Playwright must run on a real OS. Cloud function runners (Vercel/Render) can't install browser binaries. Convex/Koyeb have similar limits. |
| **Automation** | **n8n on Oracle VM** | Free cloud tier → 100 execs/month, VM → unlimited via OCI Always Free. |
| **Redis/Cache** | **Oracle VM Redis** (local install) | Prevents a second free-tier service to manage. Egress cost = $0. |
| **QA** | **Qodana + GitHub Actions** | Already have GitHub Actions for aider; Qodana adds PR-level analysis free tier |
| **Staging** | **Render Free** | Used only for staging testing. Users get Frontend (Vercel Preview) → Staging API (Render) → same Supabase/staging. |
| **CI/CD** | **GitHub Actions** | Already configured (jarvis.yml). |

---

## Free Tier vs. Cost Considerations

| Platform | Free Tier Limits | Cost Risk |
|---|---|---|
| **Oracle (Always Free)** | 4 OCPU, 24 GB RAM, 200 GB storage, 10 TB egress/month | $0 guaranteed; just keep VM running |
| **Supabase Free** | 500 MB DB, 2 GB file storage, 50k MAU, 10k req/s | Free at this project scale |
| **Vercel Free** | 100 GB bandwidth, unlimited static sites | Frontend fit well within free tier; static SPA |
| **Render Free** | 750 compute hours/month, web service sleeps after 15 min of inactivity | Only used for staging — safe |
| **Qodana Free** | 1 active analysis, 10 per month | QA only — fine |
| **Scaleway / Koyeb / Appwrite** | Available as contingency or add-ons: e.g. run the weekly email digest as a Koyeb cron job, or Sponsored email logs storage on Scaleway Object Storage (11 GB free) if Oracle runs out of volume | $0 to try |

---

## Staging vs. Production Environments

```
STAGING
  Frontend  → Vercel Preview (auto PR deployments)
  Backend   → Render Free Web Service (staging branch deploys)
  DB        → Supabase project nocturne-staging
  Scraper   → Render cron job (every 4 hours, staging config)
  N8N       → Render cron webhooks (no n8n on staging to save credits)

PRODUCTION
  Frontend  → Vercel Production (domain: noocturne.com)
  Backend   → Oracle Cloud VM (SLA-free, but scalable)
  DB        → Supabase project nocturne-prod
  Scraper   → Oracle systemd timer (every 6h production)
  N8N       → Oracle VM self-hosted n8n (unlimited)
  Cache     → Oracle Redis
  Backup    → PostgreSQL pg_dump to Supabase Storage nightly
  Backup   PG → https://cloud.oracle.com/storage/object-storage (11GB free standard)
```

---

## Rollout Order

1. **Oracle VM** — provision, Postgres, systemd setup, nginx, SSL
2. **Supabase** — create project, tables, RLS policies, get keys
3. **Backend** — deploy FastAPI as systemd service, verify `/health`
4. **Nginx** — route `api.nocturne.com` → localhost:8000, SSL
5. **Scraper cron** — run on Oracle, verify events → Supabase
6. **n8n** — import workflow, test daily scrape trigger
7. **Vercel** — connect repo, deploy frontend, set env vars
8. **Qodana** — add GitHub Actions lane for PR linting
9. **Staging** — Render web service + staging Supabase project
10. **Monitoring** — Prometheus or simple uptime check on `/health`

---

## Key Decisions Explained

### Why not Render / Railway for the API?
Both have a 10s time limit on HTTP requests. `/scrape/all` can take 15-60s depending on how many cities are active. The API also needs to run Playwright browser scrapers as subprocesses — neither platform supports installing browser binaries.

### Why not Vercel serverless functions for backend?
Vercel Functions have a 10s timeout (free tier), require stateless architecture, and don't allow custom `systemctl`-style background services for the scraper daemon. The backend here is stateful (DB connections, email sessions, Playwright subprocesses).

### Why not Appwrite?
Appwrite is a BaaS (Backend-as-a-Service) and is built as an opinionated auth/db/storage layer. Porting a custom FastAPI application to it would require rewriting all endpoints as Appwrite functions and rewriting the scraper as a separate service — too much friction when you already have working Python code.

### Why not Convex?
Convex is a real-time backend platform built around TypeScript server functions. Your backend is FastAPI Python. Reimplementing the entire scraping → sync bridge as Convex actions is a full rewrite and loses Playwright subprocess control.

### Why not a separate backend instance per city?
The scraper runs sequentially, merges results, and is `all_events.json` driven. Scaling by city adds race conditions to the deduplication tracker and Supabase sync. Keep it on one host until you prove you are saturating the 4 OCPU baseline of Oracle Free.

---

## Environment Isolation

```
API keys, DB passwords → stored in systemd Environment= lines (not in git)
  or use: credential-store / sops / AWS Secrets Manager if you prefer

Supabase keys:
  - SUPABASE_KEY (anon) → safe to set in Vercel env and frontend context
  - SUPABASE_SERVICE_ROLE_KEY → NEVER expose to frontend, only backend
```

---

## Open Questions / Decisions Needed

| Item | Decision needed |
|---|---|
| Oracle VM size | ARM (4 OCPU, 24 GB) vs x86 E2.1.Micro (1 OCPU, 8 GB) — ARM has more free eligible resources for some regions |
| Domain name | Choose domain and DNS provider (nocturne.com, Cloudflare, etc.) |
| Supabase regions | Writes from Oracle VM → Supabase free tier egress cost (free within close regions). Test round-trip latency between Oracle region and chosen Supabase region |
| SMTP provider | SendGrid / Mailgun / Oracle email delivery / any SMTP relay |
| Database backup schedule | pg_dump nightly → Supabase Storage or OCI Object Storage |

---

*Document version: 1.0*
*Generated from codebase analysis on 2026-05-19*
