#!/usr/bin/env bash
# Run this from your LOCAL WSL to complete the tambi VM deployment.
# It fixes SSH key permissions, waits for cloud-init, runs vm-setup.sh on the VM,
# then offers to restore the local Postgres dump.
set -euo pipefail

VM_IP="20.70.184.250"
VM_USER="azureuser"
WIN_KEY="/mnt/c/Users/adrian.cioanca/.ssh/id_rsa"
WSL_KEY="$HOME/.ssh/id_rsa_tambi"

# ── 1. Fix SSH key permissions ───────────────────────────────────────────────
if [ ! -f "$WSL_KEY" ]; then
  cp "$WIN_KEY" "$WSL_KEY"
  chmod 600 "$WSL_KEY"
  echo "SSH key copied to $WSL_KEY"
fi
SSH="ssh -i $WSL_KEY -o StrictHostKeyChecking=no"
SCP="scp -i $WSL_KEY -o StrictHostKeyChecking=no"

# ── 2. Wait for VM to accept SSH ─────────────────────────────────────────────
echo "Waiting for VM at $VM_IP..."
until $SSH -o ConnectTimeout=5 "$VM_USER@$VM_IP" true 2>/dev/null; do
  printf '.'; sleep 5
done
echo " connected."

# ── 3. Rsync repo to VM first (private repo — can't git clone without auth) ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
echo "Copying repo to VM..."
$SSH "$VM_USER@$VM_IP" "mkdir -p ~/tambi"
rsync -az --exclude='.venv' --exclude='node_modules' --exclude='backend/data' \
  --exclude='.git' --exclude='frontend/dist' \
  -e "ssh -i $WSL_KEY -o StrictHostKeyChecking=no" \
  "$REPO_DIR/" "$VM_USER@$VM_IP:~/tambi/"
echo "Repo copied."

# ── 4. Run vm-setup.sh on the VM ─────────────────────────────────────────────
echo "Running vm-setup.sh on the VM..."
$SSH "$VM_USER@$VM_IP" "chmod +x ~/vm-setup.sh && bash ~/vm-setup.sh"

# ── 5. Offer to restore local Postgres data ───────────────────────────────────
echo ""
read -rp "Restore local Postgres data to VM? (y/N): " DO_RESTORE
if [[ "${DO_RESTORE,,}" == "y" ]]; then
  DUMP="/tmp/tambi_pg_dump_$(date +%Y%m%d_%H%M%S).sql"
  echo "Dumping local DB to $DUMP..."
  pg_dump -h localhost -U dcih dcih > "$DUMP"

  echo "Copying dump to VM..."
  $SCP "$DUMP" "$VM_USER@$VM_IP:~/tambi_dump.sql"

  echo "Restoring on VM..."
  $SSH "$VM_USER@$VM_IP" "
    cd ~/tambi/docker
    docker compose -f docker-compose.yml -f docker-compose.vm.yml exec -T postgres \
      psql -U dcih dcih < ~/tambi_dump.sql
    echo 'Restore complete.'
  "
  rm -f "$DUMP"
fi

echo ""
echo "=== Deployment complete ==="
echo "Frontend: http://$VM_IP"
echo "Backend:  http://$VM_IP:8000/api/v1/health"
