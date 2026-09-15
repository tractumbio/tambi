#!/usr/bin/env bash
# Push local changes and redeploy on the tambi VM.
# Usage: ./scripts/redeploy-vm.sh [optional commit message]
set -euo pipefail

VM_IP="20.70.184.250"
VM_USER="azureuser"
WSL_KEY="$HOME/.ssh/id_rsa_tambi"
SSH="ssh -i $WSL_KEY -o StrictHostKeyChecking=no"
MSG="${1:-redeploy}"

# ── 1. Push latest code ───────────────────────────────────────────────────────
cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "$MSG

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
fi
git push origin dev
echo "Pushed to dev."

# ── 2. Pull and rebuild on VM ─────────────────────────────────────────────────
echo "Deploying on VM..."
$SSH "$VM_USER@$VM_IP" "
  set -e
  cd ~/tambi
  git pull
  cd docker
  docker compose -f docker-compose.yml -f docker-compose.vm.yml up -d --build
  echo 'Done.'
"

echo ""
echo "Frontend: http://$VM_IP"
echo "Backend:  http://$VM_IP:8000/api/v1/health"
