#!/usr/bin/env bash
# Run on the VM. Loads the image (if sandbox.tar.gz is present) and starts Jupyter.
set -euo pipefail
cd "$(dirname "$0")"
[ -f sandbox.tar.gz ] && docker load < sandbox.tar.gz
mkdir -p work
docker run --rm -it --name sandbox -p 8888:8888 -v "$PWD/work:/work" sandbox:latest
