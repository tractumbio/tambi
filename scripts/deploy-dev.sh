#!/usr/bin/env bash
# TAMBI — one-shot dev deployment to Azure Container Apps.
#
# Prereqs: az CLI logged in (`az login`), a resource group, and these env vars set:
#   ANTHROPIC_API_KEY, OPENAI_API_KEY, PG_ADMIN_PASSWORD
# Usage:   RG=tambi-dev-rg ./scripts/deploy-dev.sh
set -euo pipefail

RG="${RG:-tambi-dev-rg}"
LOCATION="${LOCATION:-australiaeast}"
PREFIX="${PREFIX:-tambi-dev}"
ACR="$(echo "${PREFIX}acr" | tr -d '-')"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%s)"

: "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY}"
: "${OPENAI_API_KEY:?set OPENAI_API_KEY}"
: "${PG_ADMIN_PASSWORD:?set PG_ADMIN_PASSWORD}"

echo "==> Resource group + ACR"
az group create -n "$RG" -l "$LOCATION" -o none
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true -o none 2>/dev/null || true
ACR_SERVER="$(az acr show -n "$ACR" -g "$RG" --query loginServer -o tsv)"

echo "==> Build backend image in ACR"
az acr build -r "$ACR" -t "tambi-backend:$TAG" ./backend -o none

echo "==> First deploy (backend) to learn its public URL"
# Placeholder frontend image for the first pass (backend image is the real one).
az deployment group create -g "$RG" -f infra/main.bicep -o none \
  -p namePrefix="$PREFIX" \
     backendImage="$ACR_SERVER/tambi-backend:$TAG" \
     frontendImage="$ACR_SERVER/tambi-backend:$TAG" \
     postgresAdminPassword="$PG_ADMIN_PASSWORD" \
     anthropicApiKey="$ANTHROPIC_API_KEY" \
     openaiApiKey="$OPENAI_API_KEY"

BACKEND_URL="$(az containerapp show -n "${PREFIX}-backend" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"

echo "==> Build frontend image pointing at https://$BACKEND_URL/api/v1"
az acr build -r "$ACR" -t "tambi-frontend:$TAG" \
  --build-arg VITE_API_BASE_URL="https://$BACKEND_URL/api/v1" ./frontend -o none

echo "==> Final deploy (both images)"
az deployment group create -g "$RG" -f infra/main.bicep -o none \
  -p namePrefix="$PREFIX" \
     backendImage="$ACR_SERVER/tambi-backend:$TAG" \
     frontendImage="$ACR_SERVER/tambi-frontend:$TAG" \
     postgresAdminPassword="$PG_ADMIN_PASSWORD" \
     anthropicApiKey="$ANTHROPIC_API_KEY" \
     openaiApiKey="$OPENAI_API_KEY"

FRONTEND_URL="$(az containerapp show -n "${PREFIX}-frontend" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"
echo ""
echo "==> Deployed."
echo "    Backend : https://$BACKEND_URL/api/v1/health"
echo "    Frontend: https://$FRONTEND_URL"
echo ""
echo "Next: seed reference data + first ingest via a one-off job, e.g.:"
echo "  az containerapp job create ... --command 'python -m app.ingest.backfill --from ... --to ...'"
