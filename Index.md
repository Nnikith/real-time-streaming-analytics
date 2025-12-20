# 🚀 Clean, Correct Way to Run Everything
**Real-Time Streaming Analytics Pipeline**  
_Kafka · Spark Structured Streaming · PostgreSQL · FastAPI_

This document explains the **correct startup order**, **validation steps**, and
**end-to-end verification** for the fully containerized real-time analytics system.

---

## 0️⃣ Clean Shutdown (REQUIRED)

Always start from a known-good state.

```bash
docker compose down -v
```

### Why this matters
- Stops all running services
- Clears old Kafka consumer offsets
- Removes Spark streaming checkpoints
- Prevents silent state-related bugs where metrics stop updating

> ⚠️ Skipping this step is the #1 cause of “nothing is updating” issues in streaming systems.

---

## 1️⃣ Start Infrastructure (Kafka + PostgreSQL)

Bring up **only the infrastructure services first**.

```bash
docker compose up -d zookeeper kafka postgres
```

### Verify containers are running
```bash
docker compose ps
```

### Expected output
- `zookeeper` ✅
- `kafka` ✅
- `postgres` ✅

---

## 2️⃣ Start Spark Streaming Job

Start the **stateful Spark Structured Streaming consumer**.

```bash
docker compose up -d spark-stream
```

### Follow Spark logs
```bash
docker compose logs -f spark-stream
```

### Healthy behavior
- Spark UI initializes
- No repeated stack traces
- Streaming query **keeps running** (does not exit)

Expected warning (safe to ignore):
```text
WARN ResolveWriteToStream: spark.sql.adaptive.enabled is not supported
```

---

## 3️⃣ Start Event Generator (Kafka Producer)

Start the service that continuously produces events into Kafka.

```bash
docker compose up -d event-generator
```

### Follow producer logs
```bash
docker compose logs -f event-generator
```

### Healthy behavior
- No `Connection refused` errors
- No repeating `FAIL` messages
- Continuous event production

---

## 4️⃣ Start Metrics API (FastAPI)

Build and start the API layer.

```bash
docker compose up -d --build metrics-api
```

### Health check
```bash
curl http://localhost:8000/health
```

### Expected response
```json
{"ok": true}
```

---

## 🔎 Validate End-to-End Output (MOST IMPORTANT)

If **all checks below pass**, the system is fully operational and production-valid.

---

### A️⃣ Verify Kafka Has Events

```bash
docker exec -it real-time-streaming-analytics-kafka-1 bash -lc \
"kafka-console-consumer \
 --bootstrap-server kafka:29092 \
 --topic stream.events \
 --max-messages 3"
```

✔️ You should see JSON events printed to stdout.

---

### B️⃣ Verify Spark Is Writing Metrics to PostgreSQL

```bash
docker exec -it real-time-streaming-analytics-postgres-1 bash -lc '
psql -U rt -d realtime -c "
SELECT window_start, stream_id, active_viewers
FROM stream_metrics_minute
ORDER BY window_start DESC
LIMIT 5;
"
'
```

✔️ Rows should exist and update over time.

---

### C️⃣ Verify API Exposes Metrics

Latest metrics:
```bash
curl http://localhost:8000/metrics/latest
```

Current streaming state:
```bash
curl http://localhost:8000/state
```

Historical metrics:
```bash
curl "http://localhost:8000/metrics/history?minutes=10"
```

✔️ All endpoints should return valid JSON with recent data.

---

## ✅ Success Criteria

Your pipeline is **fully functional** if:

- Kafka is receiving events
- Spark is performing windowed aggregations
- PostgreSQL is persisting metrics
- FastAPI is serving analytics endpoints

---

## 🚀 What This Proves (Interview-Ready)

You can confidently say:

> **“I built a fully containerized real-time analytics pipeline using Kafka,  
> Spark Structured Streaming, PostgreSQL, and FastAPI, including stateful viewer  
> tracking, windowed aggregations, checkpointing, and an analytics API.”**

This demonstrates **mid-to-senior level** distributed systems engineering skills.

---

## 🧠 Pro Tips

- Keep this file in the repository root
- Link it from `README.md`
- Use it during system design walkthroughs or interviews
- Treat it as a production **runbook**, not just documentation

---

## 🧩 Optional Next Steps

- Add architecture diagrams (Mermaid)
- Include failure-mode troubleshooting
- Add load-testing instructions
- Extend with CI/CD deployment steps

---



```bash
docker compose down -v                          #First: clean shutdown (important)
docker compose up -d zookeeper kafka postgres   #Start infra only (Kafka + Postgres)
docker compose ps                               #Verify
docker compose up -d spark-stream               #Start Spark streaming job
docker compose logs -f spark-stream             #Check logs for Spark streaming
docker compose up -d event-generator            #Start event generator (producer)
docker compose logs -f event-generator          #Verify
docker compose up -d --build metrics-api        #Start metrics API
curl http://localhost:8000/health               #verify, Expected Output: {"ok":true}
```



🔧 Usage
Preserve Postgres + Spark checkpoints (default)
./scripts/stop.sh

Full reset (⚠ deletes Postgres data + checkpoints)
./scripts/stop.sh no