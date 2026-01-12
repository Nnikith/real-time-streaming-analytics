#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Helpers
if [[ -f "scripts/lib.sh" ]]; then
  # shellcheck disable=SC1091
  source scripts/lib.sh
else
  info() { echo -e "[INFO] $*"; }
  log()  { echo -e "[ OK ] $*"; }
  warn() { echo -e "[WARN] $*"; }
  err()  { echo -e "[ERR ] $*" >&2; }
fi

PRESERVE_VOLUMES="${1:-yes}"   # yes | no

# Optional observability overlay
WITH_OBS="${WITH_OBS:-0}"

compose_files=(-f docker-compose.yml)
if [[ "${WITH_OBS}" == "1" && -f "docker-compose.observability.yml" ]]; then
  compose_files+=(-f docker-compose.observability.yml)
fi

dc() {
  docker compose "${compose_files[@]}" "$@"
}

echo "=========================================="
echo "🛑 Stopping Real-Time Streaming Pipeline"
echo "=========================================="

info "🧯 [1] Stop Spark (flush checkpoints)"
dc stop spark-stream || true

info "📨 [2] Stop event generator"
dc stop event-generator || true

info "🌐 [3] Stop metrics API"
dc stop metrics-api || true

if [[ "${WITH_OBS}" == "1" ]]; then
  info "📈 [obs] Stop observability"
  dc stop prometheus grafana || true
fi

info "📦 [4] Stop infra"
dc stop kafka zookeeper postgres || true

if [[ "${PRESERVE_VOLUMES}" == "no" ]]; then
  warn "🧹 [5] Removing containers + volumes (FULL RESET)"
  dc down -v || true
  warn "Volumes removed: Postgres + Spark checkpoints reset"
else
  info "🧊 [5] Removing containers only (keep volumes)"
  dc down || true
  log "Volumes preserved"
fi

echo "=========================================="
echo "✅ Pipeline stopped"
echo "=========================================="
