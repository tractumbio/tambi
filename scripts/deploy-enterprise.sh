#!/usr/bin/env bash
# Enterprise deployment: Container Apps + Azure AI Foundry + Azure OpenAI + Key Vault.
# All services authenticate via managed identity — no API keys in app config.
#
# Prerequisites:
#   az login (the account must own or have Contributor on the target subscription)
#   docker (for local build + push to ACR)
#
# Usage:
#   export PG_ADMIN_PASSWORD='<strong-password>'
#   export ANTHROPIC_API_KEY='sk-ant-...'   # optional if using Foundry for Claude
#   RG=tambi-prod-rg LOCATION=australiaeast ./scripts/deploy-enterprise.sh
set -euo pipefail

RG="${RG:-tambi-prod-rg}"
LOCATION="${LOCATION:-australiaeast}"
PREFIX="${PREFIX:-tambi-prod}"
SUBSCRIPTION=$(az account show --query id -o tsv)

echo "=== TAMBI Enterprise Deploy ==="
echo "Subscription: $SUBSCRIPTION"
echo "Resource group: $RG ($LOCATION)"
echo "Prefix: $PREFIX"

# ── Safety check: never deploy to the REGBOT subscription ────────────────────
REGBOT="be5c3299-5153-44b7-a1e4-d9b6d28b239c"
if [ "$SUBSCRIPTION" = "$REGBOT" ]; then
  echo "ERROR: Active subscription is REGBOT — aborting. Switch to the tambi account." >&2
  exit 1
fi

# ── 1. Resource group ─────────────────────────────────────────────────────────
az group create -n "$RG" -l "$LOCATION" --output none
echo "Resource group ready."

# ── 1b. Resolve existing Container Apps environment (personal subscriptions: 1 per region)
DEV_RG="${DEV_RG:-tambi-dev-rg}"
CA_ENV_ID=$(az containerapp env list -g "$DEV_RG" --query "[0].id" -o tsv 2>/dev/null || true)
if [ -z "$CA_ENV_ID" ]; then
  echo "ERROR: Could not find an existing Container Apps environment in $DEV_RG." >&2
  echo "Set DEV_RG=<rg-with-env> or create a CA environment first." >&2
  exit 1
fi
echo "Reusing CA environment: $CA_ENV_ID"

# ── 2. Initial Bicep deploy (provisions ACR, Key Vault, identities, Postgres)  ─
# Pass placeholder images — we'll update them after the images are built.
echo "Deploying infrastructure..."
DEPLOY_OUT=$(az deployment group create \
  -g "$RG" \
  -f infra/main.enterprise.bicep \
  -p namePrefix="$PREFIX" \
  -p existingCaEnvId="$CA_ENV_ID" \
  -p backendImage="mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" \
  -p frontendImage="mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" \
  -p postgresAdminPassword="$PG_ADMIN_PASSWORD" \
  -p anthropicApiKey="${ANTHROPIC_API_KEY:-}" \
  -p openaiApiKey="${OPENAI_API_KEY:-}" \
  --query properties.outputs \
  -o json)

ACR=$(echo "$DEPLOY_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['acrLoginServer']['value'])")
BACKEND_URL=$(echo "$DEPLOY_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['backendUrl']['value'])")
FRONTEND_URL=$(echo "$DEPLOY_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['frontendUrl']['value'])")
echo "ACR: $ACR"

# ── 3. Build + push images ────────────────────────────────────────────────────
az acr login -n "${ACR%%.*}"

GIT_SHA=$(git rev-parse --short HEAD)
BACKEND_IMG="$ACR/tambi-backend:$GIT_SHA"
FRONTEND_IMG="$ACR/tambi-frontend:$GIT_SHA"

echo "Building backend..."
docker build -t "$BACKEND_IMG" backend/
docker push "$BACKEND_IMG"

echo "Building frontend..."
docker build \
  --build-arg VITE_API_BASE_URL="$BACKEND_URL/api/v1" \
  -t "$FRONTEND_IMG" frontend/
docker push "$FRONTEND_IMG"

# ── 4. Redeploy with real images ─────────────────────────────────────────────
echo "Updating container apps with real images..."
az deployment group create \
  -g "$RG" \
  -f infra/main.enterprise.bicep \
  -p namePrefix="$PREFIX" \
  -p existingCaEnvId="$CA_ENV_ID" \
  -p backendImage="$BACKEND_IMG" \
  -p frontendImage="$FRONTEND_IMG" \
  -p postgresAdminPassword="$PG_ADMIN_PASSWORD" \
  -p anthropicApiKey="${ANTHROPIC_API_KEY:-}" \
  -p openaiApiKey="${OPENAI_API_KEY:-}" \
  --output none

echo ""
echo "=== Enterprise deploy complete ==="
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL/api/v1/health"
echo ""
echo "Next steps:"
echo "  1. Load data: az containerapp exec -n ${PREFIX}-backend -g $RG -- python -m app.ingest.backfill"
echo "  2. Verify managed identity auth: check backend logs for 'DefaultAzureCredential'"
echo "  3. Set up custom domain + HTTPS if needed"
