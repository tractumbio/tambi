#!/usr/bin/env bash
# Run on a machine with Docker + internet. Produces sandbox.tar.gz to copy to the VM.
set -euo pipefail
docker build -t sandbox:latest .
docker save sandbox:latest | gzip > sandbox.tar.gz
echo "Created sandbox.tar.gz"
