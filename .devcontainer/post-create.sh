#!/usr/bin/env bash
#
# PALP devcontainer post-create hook.
# Runs once when the codespace is created. Subsequent rebuilds use
# updateContentCommand instead so this stays idempotent.
#
set -euo pipefail

echo "PALP devcontainer post-create starting..."

# 1. Install backend deps
echo "[1/6] Installing backend Python deps..."
pip install --upgrade pip
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# 2. Install frontend deps
echo "[2/6] Installing frontend npm deps..."
(cd frontend && npm ci)

# 3. Install Husky pre-commit hooks (after npm ci so .husky/ exists)
echo "[3/6] Setting up Husky pre-commit hooks..."
(cd frontend && npx husky init || true)

# 4. Install Ruler globally for fast `just ruler-*` commands
echo "[4/6] Installing Ruler (AI agent rule sync)..."
npm install -g @intellectronica/ruler
ruler --version || true
ruler apply --no-gitignore --no-backup || true

# 5. Create .env from template if missing
if [[ ! -f .env ]]; then
    echo "[5/6] Creating .env from template..."
    cat > .env <<'EOF'
POSTGRES_DB=palp
POSTGRES_USER=palp
POSTGRES_PASSWORD=palp_dev_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_HOST_PORT=5437
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
REDIS_HOST_PORT=6382
BACKEND_HOST_PORT=8002
FRONTEND_HOST_PORT=3002
DJANGO_SETTINGS_MODULE=palp.settings.development
DJANGO_SECRET_KEY=dev-secret-key-not-for-production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend,0.0.0.0
PII_ENCRYPTION_KEY=fLcGmNJrJrFL_QevYxc6qK4LJiYJX_zL7nEY8K1PHZE=
NEXT_PUBLIC_API_URL=/api
BACKEND_INTERNAL_URL=http://backend:8000
SEED_PASSWORD=Pa55w0rd!
EOF
else
    echo "[5/6] .env already present, skipping."
fi

# 6. Bring up the stack and seed data
echo "[6/6] Bringing up stack and seeding data..."
docker compose up -d
sleep 10
docker exec cnhnha-backend-1 python manage.py migrate --noinput
docker cp scripts cnhnha-backend-1:/scripts
docker exec -e SEED_PASSWORD=Pa55w0rd! cnhnha-backend-1 python /scripts/seed_data.py

echo ""
echo "==========================================="
echo "  PALP devcontainer ready!"
echo "==========================================="
echo "  Frontend: http://localhost:3002"
echo "  Backend:  http://localhost:8002"
echo "  Test login:  sv_test / testpass123"
echo ""
echo "  Try: just --list"
echo "==========================================="
