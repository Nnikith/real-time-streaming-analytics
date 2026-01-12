#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Optional shared helpers (if you already have it)
if [[ -f "scripts/lib.sh" ]]; then
  # shellcheck disable=SC1091
  source scripts/lib.sh
else
  info() { echo -e "[INFO] $*"; }
  log()  { echo -e "[ OK ] $*"; }
  warn() { echo -e "[WARN] $*"; }
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

# Optional observability overlay
WITH_OBS="${WITH_OBS:-0}"
OBS_WAIT="${OBS_WAIT:-1}"

compose_files=(-f docker-compose.yml)
if [[ "${WITH_OBS}" == "1" ]]; then
  if [[ ! -f "docker-compose.observability.yml" ]]; then
    err "WITH_OBS=1 set but docker-compose.observability.yml not found."
    exit 1
  fi
  compose_files+=(-f docker-compose.observability.yml)
fi

dc() {
  docker compose "${compose_files[@]}" "$@"
}

info "=========================================="
info "🚀 Starting stack"
info "=========================================="
dc up -d --build

# Resolve container IDs dynamically (no hardcoded container names)
kafka_cid="$(dc ps -q kafka || true)"
pg_cid="$(dc ps -q postgres || true)"

if [[ -z "${kafka_cid}" || -z "${pg_cid}" ]]; then
  err "Kafka or Postgres container not found. Current services:"
  dc ps || true
  exit 1
fi

info "[1] Wait for Kafka to be healthy"
if ! wait_until_dots "Kafka healthy" 180 bash -lc \
  "docker inspect -f '{{.State.Health.Status}}' ${kafka_cid} 2>/dev/null | grep -q healthy"; then
  err "Kafka did not become healthy"
  dc ps || true
  dc logs kafka --no-color | tail -n 200 || true
  exit 1
fi
log "Kafka healthy ✅"

info "[2] Wait for Postgres to be healthy"
if ! wait_until_dots "Postgres healthy" 180 bash -lc \
  "docker inspect -f '{{.State.Health.Status}}' ${pg_cid} 2>/dev/null | grep -q healthy"; then
  err "Postgres did not become healthy"
  dc ps || true
  dc logs postgres --no-color | tail -n 200 || true
  exit 1
fi
log "Postgres healthy ✅"

info "[3] Ensure Kafka topic exists: ${TOPIC}"
docker exec -i "${kafka_cid}" bash -lc \
  "kafka-topics --bootstrap-server localhost:9092 --list | grep -qx '${TOPIC}' \
   || kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic '${TOPIC}' --partitions 1 --replication-factor 1"
log "Topic ready ✅"

info "[4] Show running services"
dc ps

# Optional observability (before smoke)
if [[ "${WITH_OBS}" == "1" ]]; then
  echo ""
  info "=========================================="
  info "📈 Observability enabled"
  info "=========================================="
  log "Prometheus: http://localhost:9090"
  log "Grafana:    http://localhost:3000 (admin/admin)"
  log "Scrape:     http://localhost:8000/prometheus"

  if [[ "${OBS_WAIT}" == "1" ]]; then
    command -v curl >/dev/null 2>&1 || { err "curl is required for OBS_WAIT=1"; exit 1; }

    info "[obs] Wait for Prometheus to be ready"
    if ! wait_until_dots "Prometheus ready" 90 curl -fsS http://localhost:9090/-/ready; then
      err "Prometheus did not become ready"
      dc ps || true
      dc logs prometheus --no-color | tail -n 200 || true
      exit 1
    fi
    log "Prometheus ready ✅"

    info "[obs] Wait for Grafana to be ready"
    if ! wait_until_dots "Grafana ready" 120 curl -fsS http://localhost:3000/api/health; then
      err "Grafana did not become ready"
      dc ps || true
      dc logs grafana --no-color | tail -n 200 || true
      exit 1
    fi
    log "Grafana ready ✅"
  else
    info "OBS_WAIT=0 set — skipping Prometheus/Grafana readiness checks."
  fi
fi

if [[ "${RUN_SMOKE}" == "1" ]]; then
  info "=========================================="
  info "🧪 Running smoke tests"
  info "=========================================="
  if [[ "${WITH_OBS}" == "1" ]]; then
    WITH_OBS=1 CHECK_OBS=1 bash scripts/smoke.sh
  else
    bash scripts/smoke.sh
  fi
else
  info "RUN_SMOKE=0 set — skipping smoke tests."
fi

log "✅ Start completed"
