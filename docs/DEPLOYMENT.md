# PALP - Deployment Guide

## Environments

| Environment | Purpose | URL |
|------------|---------|-----|
| Local | Development | localhost:3000 / localhost:8000 |
| Staging | UAT & testing | staging.palp.dau.edu.vn |
| Production | Pilot run | palp.dau.edu.vn |

## Performance SLO Targets

| Metric | Target |
|--------|--------|
| Page load p95 | <2.0s |
| Adaptive decision p95 | <1.5s |
| Dashboard load p95 | <2.0s |
| Progress update p95 | <500ms |
| Error rate | <0.5% |
| Concurrent users | 200 stable + 300 spike |
| Uptime (class hours) | >=99.9% |

SLO thresholds are defined as code in `backend/palp/settings/base.py` under `PALP_SLO`.

## Docker Deployment

### Prerequisites
- Docker Engine 24+
- Docker Compose v2+
- 4GB RAM minimum (8GB recommended)

### Development Deploy

```bash
# 1. Clone and configure
git clone <repo-url>
cd palp
cp .env.example .env

# 2. Build and start
docker-compose up -d --build

# 3. Initialize database
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser

# 4. Seed pilot data
docker-compose exec backend python manage.py shell < ../scripts/seed_data.py

# 5. Verify
curl http://localhost:8000/api/health/
curl http://localhost:8000/api/health/ready/
```

### Production Deploy

```bash
# 1. Configure production env
cp .env.example .env
# Edit .env with production values (see below)

# 2. Build and start with production compose
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Initialize database
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 4. Seed pilot data
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell < scripts/seed_data.py

# 5. Verify all health endpoints
curl http://localhost/api/health/
curl http://localhost/api/health/ready/
```

### Production Configuration

Key `.env` changes for production:

```env
DJANGO_SECRET_KEY=<generate-strong-secret>
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=palp.settings.production
DJANGO_ALLOWED_HOSTS=palp.dau.edu.vn
CORS_ALLOWED_ORIGINS=https://palp.dau.edu.vn
POSTGRES_PASSWORD=<strong-password>
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENVIRONMENT=production
APP_VERSION=1.0.0
GUNICORN_WORKERS=5
GUNICORN_THREADS=2
```

### SSL/TLS

The production compose includes an nginx reverse proxy. For HTTPS, uncomment the SSL server block in `nginx/nginx.conf` and mount your certificates:

```yaml
# Add to nginx volumes in docker-compose.prod.yml:
- /etc/ssl/palp.crt:/etc/ssl/palp.crt:ro
- /etc/ssl/palp.key:/etc/ssl/palp.key:ro
```

## Health Check System

PALP provides a 3-tier health check architecture:

### Liveness (for load balancers)
- **Endpoint:** `GET /api/health/`
- **Auth:** None required
- **Response:** `{"status": "ok"}`
- **Use case:** Load balancer / Docker health probes

### Readiness (for orchestration)
- **Endpoint:** `GET /api/health/ready/`
- **Auth:** None required
- **Response:** DB and Redis connectivity status
- **Returns:** 200 if all healthy, 503 if degraded

### Deep Health (for operators)
- **Endpoint:** `GET /api/health/deep/`
- **Auth:** Admin user required
- **Components checked:**
  - PostgreSQL query latency
  - Redis read/write latency
  - Celery worker availability
  - Celery Beat heartbeat
  - Queue depth and backlog status
  - Error rate vs SLO target

## Database Management

### Automated Backup

Production compose includes a backup service that runs daily:
- Backups stored in `postgres_backups` volume (separate from data volume)
- Compressed with gzip
- 7-day retention (configurable via `BACKUP_RETENTION_DAYS`)

### Manual Backup

```bash
docker-compose -f docker-compose.prod.yml exec db \
    pg_dump -U palp palp | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore

```bash
# Stop application services
docker-compose -f docker-compose.prod.yml stop backend celery celery-beat

# Restore
gunzip < backup_20260416.sql.gz | \
    docker-compose -f docker-compose.prod.yml exec -T db psql -U palp palp

# Restart
docker-compose -f docker-compose.prod.yml start backend celery celery-beat
```

### Migrations

```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py makemigrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

## Celery Workers

### Scheduled Tasks (Celery Beat)

| Task | Schedule | Description |
|------|----------|-------------|
| run_nightly_early_warnings | Daily 2:00 AM | Compute early warning alerts |
| generate_weekly_report | Weekly Sunday 6:00 AM | Generate KPI report |
| celery_health_ping | Every 5 minutes | Worker heartbeat sentinel |
| check_queue_backlog | Every 3 minutes | Monitor queue depth |

All schedules are defined in `CELERY_BEAT_SCHEDULE` in `backend/palp/settings/base.py`.

### Task Monitoring

Every Celery task automatically tracks:
- **Success/failure/retry counts** in Redis counters
- **Last success timestamp** per task
- **Structured JSON logs** with task name, duration, and status

### Monitor Celery

```bash
# Active tasks
docker-compose exec celery celery -A palp inspect active

# Worker stats
docker-compose exec celery celery -A palp inspect stats

# Queue depth
docker-compose exec redis redis-cli llen celery
```

### Queue Backlog Alerts

Queue depth is monitored every 3 minutes:
- **Warning** at 50 pending tasks (configurable: `QUEUE_ALERT_WARN`)
- **Critical** at 200 pending tasks (configurable: `QUEUE_ALERT_CRITICAL`)

## Monitoring

### Prometheus Metrics
- **Endpoint:** `GET /metrics/` (internal only, blocked by nginx for public)
- **Metrics available:**
  - HTTP request latency histograms (p50/p95/p99 per endpoint)
  - Request count by status code
  - Database query duration
  - Cache hit/miss rates
  - Active DB connections

### Response Time Tracking
- Every API response includes `X-Response-Time` header
- Requests >1s log a warning
- Requests >2s log an error (SLO breach)

### Error Rate Tracking
- HTTP status codes tracked per day in Redis
- Deep health check computes 5xx rate vs 0.5% SLO target

### Sentry
- Configure `SENTRY_DSN` in `.env`
- 30% trace sampling for p95 visibility
- 10% profiling for CPU hotspot detection
- Environment and release tags for filtering

### Log Access

Production uses JSON-structured logging for aggregation compatibility.

```bash
docker-compose logs -f backend
docker-compose logs -f celery
docker-compose logs -f frontend
docker-compose logs -f nginx
```

### Rate Limiting

API rate limits protect against abuse and help maintain SLO under load:
- Anonymous: 30 requests/minute
- Authenticated: 120 requests/minute
- Nginx layer: 30 requests/second with burst 60

## Performance Tuning

### Gunicorn (Backend)
- Worker class: `gthread` (optimized for I/O-bound Django)
- Workers: `CPU_COUNT * 2 + 1` (override with `GUNICORN_WORKERS`)
- Threads per worker: 2 (override with `GUNICORN_THREADS`)
- Worker recycling: every 1000 requests (prevents memory leaks)
- Timeout: 30s (aligns with DB statement_timeout)

### PostgreSQL
- Persistent connections: `CONN_MAX_AGE=600`
- Connection health checks enabled
- Statement timeout: 30s (kills runaway queries)
- Connect timeout: 5s (fast failure on DB unreachable)

### Redis
- Max memory: 256MB with LRU eviction
- Append-only persistence enabled
- Mastery state cache: 5-minute TTL
- Dashboard cache: 1-minute TTL

### Nginx
- Gzip compression for text/json/js/css
- Upstream keepalive connections
- Static file caching (30-day expiry)
- Connection and request rate limiting

## Launch Checklist

Before pilot launch, verify:

- [ ] Data mapping confirmed by GV
- [ ] Assessment stable (tested with 5+ users)
- [ ] Consent wording approved
- [ ] Dashboard GV usable (UAT feedback positive)
- [ ] SSL/TLS configured
- [ ] RBAC permissions verified
- [ ] Seed data for pilot course loaded
- [ ] Student accounts created
- [ ] **Health checks all passing** (`/api/health/ready/`)
- [ ] **Deep health check green** (`/api/health/deep/`)
- [ ] **Sentry configured and receiving events**
- [ ] **Prometheus metrics endpoint accessible**
- [ ] **Backup service running** (check `postgres_backups` volume)
- [ ] **Celery Beat schedule active** (verify `celery_health_ping` in logs)
- [ ] **Queue alerting thresholds configured**
- [ ] **Rate limiting tested** (verify 429 responses)
- [ ] **Response times within SLO** (check `X-Response-Time` headers)
- [ ] **Error rate below 0.5%** (check deep health)

## Rollback Procedure

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore database from backup
docker-compose -f docker-compose.prod.yml up -d db
sleep 10
gunzip < /path/to/backup_previous.sql.gz | \
    docker-compose -f docker-compose.prod.yml exec -T db psql -U palp palp

# Rebuild with previous code version
git checkout <previous-tag>
docker-compose -f docker-compose.prod.yml up -d --build

# Verify
curl http://localhost/api/health/ready/
```
