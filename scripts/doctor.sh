#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# doctor.sh — Full environment + stack diagnostics for:
# Kafka → Spark Structured Streaming → Postgres → FastAPI
# (and optionally Prometheus → Grafana if present in the active compose config)
#
# Usage:
#   ./scripts/doctor.sh
#
# Optional env vars:
#   TOPIC=stream.events
#   API_URL=http://localhost:8000
#   SHOW_LOGS=0|1
#   LOG_TAIL=200
#   PROM_URL=http://localhost:9090
#   GRAFANA_URL=http://localhost:3000
#
# READ-ONLY:
# - No topics created
# - No volumes wiped
# - No config mutated
#
# Exit codes:
#   0 = healthy
#   1 = issues detected
# ============================================================================

RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

ok()    { echo "${GREEN}✅${RESET} $*"; }
warn()  { echo "${YELLOW}⚠️${RESET}  $*"; }
fail()  { echo "${RED}❌${RESET} $*"; }
info()  { echo "${BLUE}ℹ️${RESET}  $*"; }
hr()    { echo "-------------------------------------------------------------------------------"; }
title() { echo ""; echo "${BOLD}$*${RESET}"; hr; }

SHOW_LOGS="${SHOW_LOGS:-0}"
LOG_TAIL="${LOG_TAIL:-200}"
TOPIC="${TOPIC:-${KAFKA_TOPIC:-stream.events}}"
API_URL="${API_URL:-http://localhost:8000}"
PROM_URL="${PROM_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

EXIT_STATUS=0
ISSUES=()

add_issue() {
  EXIT_STATUS=1
  ISSUES+=("$1")
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

compose() { docker compose "$@"; }

svc_cid() {
  compose ps -q "$1" 2>/dev/null || true
}

cid_running() {
  local cid="$1"
  [[ -n "$cid" ]] || return 1
  docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null | grep -q true
}

cid_health() {
  local cid="$1"
  [[ -n "$cid" ]] || { echo "missing"; return 0; }
  docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo "unknown"
}

show_tail_logs() {
  [[ "$SHOW_LOGS" == "1" ]] || return 0
  echo ""
  info "Tail logs: $1 (last ${LOG_TAIL} lines)"
  compose logs --no-color "$1" | tail -n "$LOG_TAIL" || true
}

port_in_use() {
  local port="$1"
  if have_cmd lsof; then
    lsof -iTCP -sTCP:LISTEN -P 2>/dev/null | grep -q ":${port} " && return 0 || return 1
  elif have_cmd ss; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(:|\\[)${port}\$" && return 0 || return 1
  elif have_cmd netstat; then
    netstat -an 2>/dev/null | grep -q LISTEN | grep -qE "[:.]${port} " && return 0 || return 1
  else
    return 2
  fi
}

has_service() {
  # Returns 0 if service name appears in the active compose config
  compose config --services 2>/dev/null | grep -qx "$1"
}

echo "${BOLD}🩺 Doctor — Real-Time Streaming Pipeline Diagnostics${RESET}"
echo "Topic:    ${TOPIC}"
echo "API:      ${API_URL}"
echo "Prom:     ${PROM_URL}"
echo "Grafana:  ${GRAFANA_URL}"
hr

# ----------------------------------------------------------------------------
title "1) Host Environment"

have_cmd docker && ok "docker found" || { fail "docker missing"; add_issue "docker missing"; }

docker info >/dev/null 2>&1 && ok "docker daemon running" || { fail "docker daemon not running"; add_issue "docker daemon down"; }

docker compose version >/dev/null 2>&1 && ok "docker compose available" || { fail "docker compose missing"; add_issue "compose missing"; }

# ----------------------------------------------------------------------------
title "Host Port Availability"

# Always check base ports
BASE_PORTS=(9092 5432 8000)

# Optionally check observability ports if those services exist in the active config
OBS_PORTS=()
if has_service prometheus; then OBS_PORTS+=(9090); fi
if has_service grafana; then OBS_PORTS+=(3000); fi

for p in "${BASE_PORTS[@]}" "${OBS_PORTS[@]}"; do
  if port_in_use "$p"; then
    warn "Port $p in use on host"
    add_issue "port $p in use"
  else
    ok "Port $p free"
  fi
done

# ----------------------------------------------------------------------------
title "2) Repo Structure"

for f in docker-compose.yml scripts/start.sh scripts/stop.sh scripts/smoke.sh scripts/lib.sh; do
  [[ -f "$f" ]] && ok "Found $f" || { fail "Missing $f"; add_issue "missing $f"; }
done

[[ -f .env ]] && warn ".env exists (ensure gitignored)" || info ".env not present"
[[ -f .env.example ]] && ok ".env.example present" || { warn ".env.example missing"; add_issue ".env.example missing"; }

if [[ -f .gitignore ]]; then
  ok ".gitignore present"
  grep -qE '(^|/)\.env(\s|$)' .gitignore && ok ".env gitignored" || { warn ".env not gitignored"; add_issue ".env not gitignored"; }
else
  warn ".gitignore missing"
  add_issue ".gitignore missing"
fi

# ----------------------------------------------------------------------------
title "3) Docker Compose Stack"

compose config >/dev/null 2>&1 && ok "compose config valid" || { fail "compose config invalid"; add_issue "compose invalid"; }

compose ps || { warn "compose ps failed"; add_issue "compose ps failed"; }

# Base services always expected
SERVICES=(zookeeper kafka postgres event-generator spark-stream metrics-api)

# Optional services if present in active config
if has_service prometheus; then SERVICES+=(prometheus); fi
if has_service grafana; then SERVICES+=(grafana); fi

title "Service Status"
for svc in "${SERVICES[@]}"; do
  cid="$(svc_cid "$svc")"
  [[ -z "$cid" ]] && { warn "$svc not running"; add_issue "$svc missing"; continue; }

  cid_running "$cid" && ok "$svc running" || { fail "$svc stopped"; add_issue "$svc stopped"; show_tail_logs "$svc"; }

  case "$(cid_health "$cid")" in
    healthy) ok "$svc healthy" ;;
    none) warn "$svc no healthcheck" ;;
    unhealthy) fail "$svc unhealthy"; add_issue "$svc unhealthy"; show_tail_logs "$svc" ;;
    *) warn "$svc health unknown" ;;
  esac
done

# ----------------------------------------------------------------------------
title "4) Kafka Checks"

kafka_cid="$(svc_cid kafka)"
if [[ -z "$kafka_cid" ]]; then
  fail "Kafka missing"
  add_issue "kafka missing"
else
  docker exec "$kafka_cid" kafka-topics --bootstrap-server localhost:9092 --list | grep -qx "$TOPIC" \
    && ok "Kafka topic exists" || { fail "Kafka topic missing"; add_issue "topic missing"; }

  off="$(docker exec "$kafka_cid" kafka-run-class kafka.tools.GetOffsetShell \
        --broker-list localhost:9092 --topic "$TOPIC" 2>/dev/null | awk -F: '{s+=$3} END{print s+0}')"

  ok "Kafka offsets: ${off}"
  [[ "$off" -eq 0 ]] && { warn "Kafka offsets = 0"; add_issue "no kafka data"; }
fi

# ----------------------------------------------------------------------------
title "5) Postgres Checks"

pg_cid="$(svc_cid postgres)"
if [[ -z "$pg_cid" ]]; then
  fail "Postgres missing"
  add_issue "postgres missing"
else
  docker exec "$pg_cid" pg_isready -U rt -d realtime >/dev/null \
    && ok "Postgres ready" || { fail "Postgres not ready"; add_issue "postgres not ready"; }

  docker exec "$pg_cid" psql -U rt -d realtime -tAc \
    "SELECT to_regclass('public.stream_metrics_minute')" | grep -q stream_metrics_minute \
    && ok "stream_metrics_minute exists" || { fail "Missing stream_metrics_minute"; add_issue "table missing"; }

  docker exec "$pg_cid" psql -U rt -d realtime -tAc \
    "SELECT COUNT(*) FROM stream_metrics_minute WHERE window_start > now() - interval '5 minutes'" \
    | awk '{exit !($1>0)}' \
    && ok "Recent rows present" || { warn "No recent rows"; add_issue "no postgres writes"; }
fi

# ----------------------------------------------------------------------------
title "6) Spark Checks"

spark_cid="$(svc_cid spark-stream)"
if [[ -z "$spark_cid" ]]; then
  fail "Spark missing"
  add_issue "spark missing"
else
  docker exec "$spark_cid" test -w /tmp -a -w /tmp/.ivy2 -a -w /opt/spark-checkpoints \
    && ok "Spark writable dirs OK" || { fail "Spark perms broken"; add_issue "spark perms"; }

  compose logs spark-stream | grep -qE "basedir must be absolute|/tmp/.ivy2" \
    && { fail "Spark Ivy errors"; add_issue "ivy errors"; show_tail_logs spark-stream; } \
    || ok "No Ivy errors detected"

  compose logs spark-stream | grep -qE "StreamingQuery|MicroBatchExecution" \
    && ok "Spark streaming started" || { warn "Spark streaming not detected"; add_issue "spark not streaming"; }
fi

# ----------------------------------------------------------------------------
title "7) FastAPI Checks"

have_cmd curl && ok "curl available" || { fail "curl missing"; add_issue "curl missing"; }

curl -fsS "$API_URL/health" | grep -q '"ok":true' \
  && ok "/health OK" || { warn "/health failed"; add_issue "api health"; }

metrics="$(curl -fsS "$API_URL/metrics" || true)"
echo "$metrics" | grep -q '"rows"' && echo "$metrics" | grep -q '"latest_window_start"' \
  && ok "/metrics shape OK" || { warn "/metrics invalid"; add_issue "api metrics"; }

# ----------------------------------------------------------------------------
title "8) Observability Checks (Optional)"

# Prometheus checks only if service exists in config
if has_service prometheus; then
  title "Prometheus Checks"

  # Readiness endpoint
  if curl -fsS "${PROM_URL}/-/ready" >/dev/null 2>&1; then
    ok "Prometheus ready"
  else
    fail "Prometheus not ready"
    add_issue "prometheus not ready"
    show_tail_logs prometheus
  fi

  # Target health: best-effort without jq
  targets="$(curl -fsS "${PROM_URL}/api/v1/targets?state=active" 2>/dev/null || true)"
  if echo "$targets" | grep -qE '"health":"up"' && echo "$targets" | grep -qE 'metrics-api:8000|localhost:8000'; then
    ok "Prometheus scraping metrics API (target UP)"
  else
    warn "Prometheus target for metrics API not confirmed UP"
    add_issue "prometheus scrape target"
  fi
else
  info "Prometheus not in active compose config; skipping"
fi

# Grafana checks only if service exists in config
if has_service grafana; then
  title "Grafana Checks"

  if curl -fsS "${GRAFANA_URL}/api/health" | grep -q '"database":"ok"'; then
    ok "Grafana healthy"
  else
    fail "Grafana health check failed"
    add_issue "grafana unhealthy"
    show_tail_logs grafana
  fi
else
  info "Grafana not in active compose config; skipping"
fi

# ----------------------------------------------------------------------------
title "9) Summary"

if [[ "$EXIT_STATUS" -eq 0 ]]; then
  ok "All checks passed 🎉"
else
  fail "Issues detected"
  echo ""
  echo "${BOLD}Findings:${RESET}"
  for i in "${ISSUES[@]}"; do echo " - $i"; done
fi

exit "$EXIT_STATUS"
