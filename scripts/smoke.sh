#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source scripts/lib.sh

TOPIC="${KAFKA_TOPIC:-stream.events}"

echo "=========================================="
echo "🧪 Smoke Tests (Kafka → Spark → Postgres → API)"
echo "=========================================="

need_cmd curl
need_cmd docker

# Resolve container IDs
pg_cid="$(docker compose ps -q postgres || true)"
kafka_cid="$(docker compose ps -q kafka || true)"
spark_cid="$(docker compose ps -q spark-stream || true)"

missing=()
[[ -n "$pg_cid" ]] || missing+=("postgres")
[[ -n "$kafka_cid" ]] || missing+=("kafka")
[[ -n "$spark_cid" ]] || missing+=("spark-stream")

if (( ${#missing[@]} > 0 )); then
  err "Missing containers: ${missing[*]}"
  docker compose ps || true
  exit 1
fi

info "[1] Kafka topic exists"
docker exec -i "${kafka_cid}" bash -lc "kafka-topics --bootstrap-server localhost:9092 --describe --topic '${TOPIC}' >/dev/null"
log "Topic OK: ${TOPIC}"

info "[2] Verify Kafka offsets advance (producer is alive)"
before="$(docker exec -i "${kafka_cid}" bash -lc "kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic '${TOPIC}' | awk -F: '{sum+=\$3} END{print sum+0}'")"
sleep 3
after="$(docker exec -i "${kafka_cid}" bash -lc "kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic '${TOPIC}' | awk -F: '{sum+=\$3} END{print sum+0}'")"

info "Offsets before=${before} after=${after}"
if (( after <= before )); then
  err "Kafka offsets did not advance. Producer may not be publishing."
  exit 1
fi
log "Offsets advancing ✅"

info "[3] Spark container is running + healthy"
wait_until_dots "Spark healthy" 120 bash -lc '
  cid="$(docker compose ps -q spark-stream)";
  test -n "$cid" &&
  docker inspect -f "{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" "$cid" \
    | grep -q "^true healthy$"
'
log "Spark healthy ✅"

info "[4] Spark → Postgres: confirm table has recent rows (last 5 minutes)"
wait_until_dots "Postgres has recent rows in stream_metrics_minute" 150 bash -lc \
  "docker exec -i ${pg_cid} bash -lc \
   \"psql -U rt -d realtime -tAc \\\"SELECT COUNT(*) FROM stream_metrics_minute WHERE window_start > NOW() - interval '5 minutes'\\\" \
     | grep -E '^[0-9]+' | awk '{exit !(\\\$1>0)}'\""

info "[4b] Produce a deterministic donation event (self-contained check)"
don_id="smoke-donation-$(date +%s)"
don_ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
don_stream="stream_1001"
don_amount="25.0"
don_json="$(cat <<EOF
{"event_id":"${don_id}","ts":"${don_ts}","event_type":"donation","stream_id":"${don_stream}","user_id":"smoke_user","amount_usd":${don_amount}}
EOF
)"
docker exec -i "${kafka_cid}" bash -lc \
  "echo '${don_json}' | kafka-console-producer --bootstrap-server localhost:9092 --topic '${TOPIC}' >/dev/null"
log "Produced donation event_id=${don_id} amount_usd=${don_amount} stream_id=${don_stream}"

info "[4c] Verify Postgres reflects the donation (donations_usd > 0 in last 5 minutes)"
wait_until_dots "Postgres has donations_usd > 0 (recent)" 150 bash -lc \
  "docker exec -i ${pg_cid} bash -lc \
   \"psql -U rt -d realtime -tAc \\\" \
      SELECT COUNT(*) \
      FROM stream_metrics_minute \
      WHERE stream_id='${don_stream}' \
        AND donations_usd > 0 \
        AND window_start > NOW() - interval '5 minutes' \
   \\\" \
     | grep -E '^[0-9]+' | awk '{exit !(\\\$1>0)}'\""
log "Donations aggregation OK 💰✅"

docker exec -i "${pg_cid}" bash -lc \
  "psql -U rt -d realtime -c \"
   SELECT window_start, stream_id, active_viewers, chat_messages, donations_usd
   FROM stream_metrics_minute
   ORDER BY window_start DESC
   LIMIT 3;\"" >/dev/null
log "Postgres write OK ✅"

info "[5] API health + metrics shape"
curl -fsS http://localhost:8000/health | grep -q '"ok":true' || { err "Health endpoint failed"; exit 1; }
log "API /health OK ✅"

json="$(curl -fsS http://localhost:8000/metrics)"
echo "$json" | grep -q '"rows"' || { err "/metrics missing rows"; exit 1; }
echo "$json" | grep -q '"latest_window_start"' || { err "/metrics missing latest_window_start"; exit 1; }
log "API /metrics shape OK ✅"

# Optional observability checks
if [[ "${WITH_OBS:-0}" == "1" || "${CHECK_OBS:-0}" == "1" ]]; then
  echo ""
  info "[6] Observability checks (Prometheus + Grafana + /prometheus)"

  # Prometheus ready
  curl -fsS http://localhost:9090/-/ready >/dev/null || { err "Prometheus not ready"; exit 1; }
  log "Prometheus ready ✅"

  # Grafana ready
  curl -fsS http://localhost:3000/api/health >/dev/null || { err "Grafana not ready"; exit 1; }
  log "Grafana ready ✅"

  # API /prometheus endpoint
  prom="$(curl -fsS http://localhost:8000/prometheus)"
  echo "$prom" | grep -q '^api_http_requests_total' || { err "/prometheus missing api_http_requests_total"; exit 1; }
  echo "$prom" | grep -q '^api_http_request_duration_seconds_bucket' || { err "/prometheus missing api_http_request_duration_seconds_bucket"; exit 1; }
  log "API /prometheus OK ✅"

  # Prometheus sees API target (simple presence check)
  curl -fsS http://localhost:9090/api/v1/targets | grep -q 'metrics-api:8000' || { err "Prometheus does not list metrics-api target"; exit 1; }
  log "Prometheus target present ✅"
fi

echo "=========================================="
echo "✅ Smoke tests passed"
echo "=========================================="
