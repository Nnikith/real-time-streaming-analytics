#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Flags inherited from Makefile
WITH_OBS="${WITH_OBS:-0}"
OBS_WAIT="${OBS_WAIT:-1}"
RUN_SMOKE="${RUN_SMOKE:-1}"

echo "=========================================="
if [[ "${WITH_OBS}" == "1" ]]; then
  echo "♻️  Resetting FULL pipeline (wipe volumes + observability)"
else
  echo "♻️  Resetting pipeline (wipe volumes)"
fi
echo "=========================================="

# Equivalent behavior:
#   base reset:      make down (wipe) + make up
#   full reset:      make full-down + make full-up
WITH_OBS="${WITH_OBS}" bash scripts/stop.sh no
WITH_OBS="${WITH_OBS}" OBS_WAIT="${OBS_WAIT}" RUN_SMOKE="${RUN_SMOKE}" bash scripts/start.sh

echo "=========================================="
echo "✅ Reset completed"
echo "=========================================="
