#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=========================================="
echo "♻️ Resetting Pipeline (wipe volumes)"
echo "=========================================="

scripts/stop.sh no
scripts/start.sh
