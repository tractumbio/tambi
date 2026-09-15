#!/usr/bin/env bash
# CI-only: build the real TAMBI images, push them to the enterprise ACR, and roll
# them onto the already-provisioned Container Apps. Infrastructure, Key Vault
# references, role assignments and env vars are owned by main.enterprise.bicep and
# are NOT touched here — this only swaps the container images, so it needs just
# AcrPush on the registry + Contributor on tambi-prod-rg (no role-assignment rights).
set -euo pipefail

RG="${RG:-tambi-prod-rg}"
PREFIX="${PREFIX:-tambi-prod}"
ACR_NAME="$(printf '%s' "${PREFIX}acr" | tr -d '-')"   # tambi-prod -> tambiprodacr
ACR_SERVER="${ACR_NAME}.azurecr.io"

# ── Safety: never operate on the REGBOT subscription ─────────────────────────
SUB=$(az account show --query id -o tsv | tr -d '[:space:]')
EXPECTED="187d1a3e-385a-4714-b7bf-da248b8fb25b"
REGBOT="be5c3299-5153-44b7-a1e4-d9b6d28b239c"
if [ "$SUB" = "$REGBOT" ] || [ "$SUB" != "$EXPECTED" ]; then
  echo "ERROR: subscription '$SUB' is not the expected tambi account ($EXPECTED). Aborting." >&2
  exit 1
fi

TAG="$(git rev-parse --short HEAD)"
BACKEND_IMG="${ACR_SERVER}/tambi-backend:${TAG}"
FRONTEND_IMG="${ACR_SERVER}/tambi-frontend:${TAG}"

az acr login -n "$ACR_NAME"

echo "Building backend image ${BACKEND_IMG}..."
docker build -t "$BACKEND_IMG" backend/
docker push "$BACKEND_IMG"

BACKEND_FQDN=$(az containerapp show -n "${PREFIX}-backend" -g "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)
echo "Backend FQDN: ${BACKEND_FQDN}"

echo "Building frontend image ${FRONTEND_IMG}..."
docker build --build-arg VITE_API_BASE_URL="https://${BACKEND_FQDN}/api/v1" \
  -t "$FRONTEND_IMG" frontend/
docker push "$FRONTEND_IMG"

echo "Rolling new images onto the Container Apps..."
az containerapp update -n "${PREFIX}-backend"  -g "$RG" --image "$BACKEND_IMG"  -o none
az containerapp update -n "${PREFIX}-frontend" -g "$RG" --image "$FRONTEND_IMG" -o none

FRONTEND_FQDN=$(az containerapp show -n "${PREFIX}-frontend" -g "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "=== Enterprise images deployed ==="
echo "Frontend: https://${FRONTEND_FQDN}"
echo "Backend:  https://${BACKEND_FQDN}/api/v1/health"
