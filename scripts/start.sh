#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Optional shared helpers (if you already have it)
if [[ -f "scripts/lib.sh" ]]; then
  # shellcheck disable=SC1091
  source scripts/lib.sh
else
  # Minimal fallback helpers if lib.sh isn't present
  info() { echo -e "[INFO] $*"; }
  log()  { echo -e "[ OK ] $*"; }
  err()  { echo -e "[ERR ] $*" >&2; }
  wait_until_dots() {
    local msg="$1" timeout="$2"; shift 2
    local start; start="$(date +%s)"
    echo -n "${msg}"
    while true; do
      if "$@" >/dev/null 2>&1; then
        echo ""
        return 0
      fi
      echo -n "."
      sleep 2
      local now; now="$(date +%s)"
      if (( now - start >= timeout )); then
        echo ""
        return 1
      fi
    done
  }
fi

TOPIC="${KAFKA_TOPIC:-stream.events}"
RUN_SMOKE="${RUN_SMOKE:-1}"

info "=========================================="
info "🚀 Starting stack (docker compose up -d)"
info "=========================================="

docker compose up -d --build

# Resolve container IDs dynamically (no hardcoded container names)
kafka_cid="$(docker compose ps -q kafka || true)"
pg_cid="$(docker compose ps -q postgres || true)"

if [[ -z "${kafka_cid}" || -z "${pg_cid}" ]]; then
  err "Kafka or Postgres container not found. Current services:"
  docker compose ps || true
  exit 1
fi

info "[1] Wait for Kafka to be healthy"
if ! wait_until_dots "Kafka healthy" 180 bash -lc \
  "docker inspect -f '{{.State.Health.Status}}' ${kafka_cid} 2>/dev/null | grep -q healthy"; then
  err "Kafka did not become healthy"
  docker compose ps || true
  docker compose logs kafka --no-color | tail -n 200 || true
  exit 1
fi
log "Kafka healthy ✅"

info "[2] Wait for Postgres to be healthy"
if ! wait_until_dots "Postgres healthy" 180 bash -lc \
  "docker inspect -f '{{.State.Health.Status}}' ${pg_cid} 2>/dev/null | grep -q healthy"; then
  err "Postgres did not become healthy"
  docker compose ps || true
  docker compose logs postgres --no-color | tail -n 200 || true
  exit 1
fi
log "Postgres healthy ✅"

info "[3] Ensure Kafka topic exists: ${TOPIC}"
# Create topic if missing (idempotent)
docker exec -i "${kafka_cid}" bash -lc \
  "kafka-topics --bootstrap-server localhost:9092 --list | grep -qx '${TOPIC}' \
   || kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic '${TOPIC}' --partitions 1 --replication-factor 1"
log "Topic ready ✅"

info "[4] Show running services"
docker compose ps

if [[ "${RUN_SMOKE}" == "1" ]]; then
  info "=========================================="
  info "🧪 Running smoke tests"
  info "=========================================="
  bash scripts/smoke.sh
else
  info "RUN_SMOKE=0 set — skipping smoke tests."
fi

log "✅ Start completed"
