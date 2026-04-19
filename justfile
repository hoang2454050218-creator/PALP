# PALP Justfile — task runner
# Install just: https://github.com/casey/just
# Run `just --list` to see all commands.

set shell := ["powershell", "-NoLogo", "-Command"]
set windows-shell := ["powershell", "-NoLogo", "-Command"]

# Default recipe
default:
    @just --list

# === Stack lifecycle ===

# Bring up the full dev stack
dev:
    docker compose up -d
    @echo "Backend:  http://localhost:8002"
    @echo "Frontend: http://localhost:3002"
    @echo "Postgres: localhost:5437  Redis: localhost:6382"

# Stop the full stack but keep volumes
down:
    docker compose down

# Wipe everything including volumes (DANGEROUS in prod)
clean:
    docker compose down -v --remove-orphans

# Tail logs of a service (default: backend)
logs service="backend":
    docker compose logs -f cnhnha-{{service}}-1

# Build all images
build:
    docker compose build

# === Database ===

# Run all pending migrations
migrate:
    docker exec cnhnha-backend-1 python manage.py migrate --noinput

# Create migrations for current model changes
makemigrations:
    docker exec cnhnha-backend-1 python manage.py makemigrations

# Seed dev data with predictable test accounts
seed:
    docker cp scripts cnhnha-backend-1:/scripts
    docker exec -e SEED_PASSWORD=Pa55w0rd! cnhnha-backend-1 python /scripts/seed_data.py

# Open a Django shell inside the backend container
shell:
    docker exec -it cnhnha-backend-1 python manage.py shell

# Open a psql session
psql:
    docker exec -it cnhnha-db-1 psql -U palp -d palp

# === Testing ===

# Run all tests (backend + frontend)
test: test-backend test-frontend

# Backend pytest with coverage gate
test-backend:
    cd backend && python -m pytest -m "not slow and not load and not recovery"

# Frontend Vitest + ESLint + tsc
test-frontend:
    cd frontend && npm run test:run
    cd frontend && npm run lint
    cd frontend && npx tsc --noEmit

# Run e2e Playwright tests (requires stack running)
test-e2e:
    cd frontend && npm run test:e2e

# Mutation testing for critical modules
test-mutation:
    cd backend && python -m mutmut run --paths-to-mutate=adaptive/engine.py,dashboard/services.py,events/emitter.py

# === Lint & format ===

# Run all linters
lint: lint-backend lint-frontend

lint-backend:
    cd backend && ruff check .
    cd backend && ruff format --check .
    cd backend && mypy --follow-imports=skip palp

lint-frontend:
    cd frontend && npm run lint
    cd frontend && npx tsc --noEmit

# Auto-fix lint issues
fix:
    cd backend && ruff check --fix .
    cd backend && ruff format .
    cd frontend && npm run lint -- --fix

# === Release ===

# Run release gate before tagging
release-gate:
    python scripts/release_gate.py --format text

# Bump version and create release
release type="patch":
    @echo "Releasing {{type}}: use semantic-release in CI"

# Generate OpenAPI baseline
openapi:
    docker exec cnhnha-backend-1 python manage.py spectacular --file /tmp/schema.yaml
    docker cp cnhnha-backend-1:/tmp/schema.yaml backend/openapi/schema-baseline.yaml

# === Chaos engineering ===

# Kill a random celery worker
chaos-worker-kill:
    docker stop cnhnha-celery-1
    @echo "Celery worker killed. Restarting in 30s..."
    @sleep 30
    docker compose up -d celery

# Stop redis temporarily (60s)
chaos-redis:
    docker stop cnhnha-redis-1
    @sleep 60
    docker compose up -d redis

# === Backup & restore ===

# Manual backup
backup:
    bash scripts/backup_db.sh

# Run restore drill
restore-drill:
    docker exec cnhnha-backend-1 python -c "from analytics.tasks import weekly_restore_drill; print(weekly_restore_drill())"

# === Observability ===

# Bring up observability stack (Loki + Tempo + Alertmanager)
observability:
    docker compose --profile observability up -d
    @echo "Grafana: http://localhost:3003"
    @echo "Loki:    http://localhost:3100"
    @echo "Alertmanager: http://localhost:9093"

# Open Grafana in browser
grafana:
    @powershell -Command "Start-Process http://localhost:3003"

# === Documentation ===

# Build docs site locally
docs:
    cd docs-site && npm run start

# Build static docs site
docs-build:
    cd docs-site && npm run build

# Storybook dev server
storybook:
    cd frontend && npm run storybook

# === AI Agent Rules (Ruler) ===

# Sync .ruler/ -> all 32 AI agent configs (CLAUDE.md, AGENTS.md, .cursor/, .codex/, ...)
ruler-apply:
    npx -y @intellectronica/ruler apply --verbose

# Preview ruler changes without writing files
ruler-check:
    npx -y @intellectronica/ruler apply --dry-run --verbose

# Undo all ruler-generated files (restores .bak backups when present)
ruler-revert:
    npx -y @intellectronica/ruler revert

# Validate .ruler/ structure (ruler.toml syntax + SKILL.md frontmatter)
ruler-lint:
    python scripts/validate_ruler.py

# === Health checks ===

# Quick health check on all services
health:
    @echo "Backend  /api/health/      "
    @powershell -Command "(Invoke-WebRequest -Uri http://localhost:8002/api/health/ -UseBasicParsing).StatusCode"
    @echo "Frontend /login            "
    @powershell -Command "(Invoke-WebRequest -Uri http://localhost:3002/login -UseBasicParsing).StatusCode"
    @echo "Proxy    /api/health/      "
    @powershell -Command "(Invoke-WebRequest -Uri http://localhost:3002/api/health/ -UseBasicParsing -MaximumRedirection 5).StatusCode"
