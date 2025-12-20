#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source scripts/lib.sh

PRESERVE_VOLUMES="${1:-yes}"   # yes | no

echo "=========================================="
echo "🛑 Stopping Real-Time Streaming Pipeline"
echo "=========================================="

info "🧯 [1] Stop Spark (flush checkpoints)"
docker compose stop spark-stream || true

info "📨 [2] Stop event generator"
docker compose stop event-generator || true

info "🌐 [3] Stop metrics API"
docker compose stop metrics-api || true

info "📦 [4] Stop infra"
docker compose stop kafka zookeeper postgres || true

if [[ "${PRESERVE_VOLUMES}" == "no" ]]; then
  warn "🧹 [5] Removing containers + volumes (FULL RESET)"
  docker compose down -v || true
  warn "Volumes removed: Postgres + Spark checkpoints reset"
else
  info "🧊 [5] Removing containers only (keep volumes)"
  docker compose down || true
  log "Volumes preserved"
fi

echo "=========================================="
echo "✅ Pipeline stopped"
echo "=========================================="
