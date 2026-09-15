#!/usr/bin/env bash
# One-shot VM setup: clones repo, writes .env, runs docker compose.
# Run as azureuser on the tambi-dev-vm.
set -euo pipefail

VM_IP=$(curl -sf --max-time 5 http://169.254.169.254/metadata/instance/network/interface/0/ipv4/ipAddress/0/publicIpAddress?api-version=2021-02-01&format=text || echo "20.70.184.250")
REPO_DIR="$HOME/tambi"

echo "=== TAMBI VM Setup ==="
echo "Public IP: $VM_IP"

# 1. Wait for cloud-init (Docker install) to finish
echo "Waiting for cloud-init..."
while ! command -v docker &>/dev/null; do sleep 5; done
sudo systemctl is-active docker || sudo systemctl start docker
echo "Docker ready."

# 2. Clone repo
if [ ! -d "$REPO_DIR" ]; then
  git clone https://github.com/tractumbio/tambi.git --branch dev "$REPO_DIR"
else
  cd "$REPO_DIR" && git pull
fi
cd "$REPO_DIR"

# 3. Write .env
if [ ! -f .env ]; then
  echo "--- Configuring .env ---"
  read -rp "ANTHROPIC_API_KEY: " ANTHROPIC_KEY
  read -rp "OPENAI_API_KEY:    " OPENAI_KEY

  PG_PASS="$(openssl rand -hex 16)"
  cat > .env <<EOF
ENVIRONMENT=production
LOG_LEVEL=INFO
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
API_V1_PREFIX=/api/v1
CORS_ORIGINS=*

DATABASE_URL=postgresql://dcih:${PG_PASS}@postgres:5432/dcih
DATABASE_URL_READONLY=postgresql://dcih:${PG_PASS}@postgres:5432/dcih
POSTGRES_DB=dcih
POSTGRES_USER=dcih
POSTGRES_PASSWORD=${PG_PASS}

ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
OPENAI_API_KEY=${OPENAI_KEY}

EMBEDDING_BACKEND=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

LLM_MAX_ROWS=1000
LLM_STATEMENT_TIMEOUT_MS=15000
NEWS_RELEVANCE_FLOOR=0.35
REPORT_TIMEZONE=Australia/Sydney

VITE_API_BASE_URL=http://${VM_IP}:8000/api/v1
EOF
  echo ".env written."
else
  echo ".env already exists, skipping."
fi

# 4. Start services
echo "=== Building and starting services ==="
cd "$REPO_DIR/docker"
docker compose -f docker-compose.yml -f docker-compose.vm.yml up -d --build

echo ""
echo "=== Done! ==="
echo "Frontend: http://$VM_IP"
echo "Backend:  http://$VM_IP:8000/api/v1/health"
echo ""
echo "Run migrations if this is a fresh DB:"
echo "  docker compose -f docker-compose.yml -f docker-compose.vm.yml exec backend alembic upgrade head"
