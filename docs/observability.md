# Observability

This system includes first-class observability using **Prometheus** and **Grafana**.

- The FastAPI service exposes Prometheus-compatible metrics at **`/prometheus`**
- Prometheus scrapes the metrics API
- Grafana is provisioned with a Prometheus datasource and a ready-to-use dashboard

---

## What Runs in the Full Stack

The **full stack** is the base pipeline plus observability services:

- Kafka
- Event generator
- Spark Structured Streaming
- Postgres
- FastAPI metrics API
- **Prometheus**
- **Grafana**

Start the full stack:

```bash
make full-up
```

Stop it:

```bash
make full-down
```

---

## Metrics Endpoint

The FastAPI metrics service exposes a Prometheus scrape endpoint:

```bash
curl -sS http://localhost:8000/prometheus
```

This endpoint is what Prometheus scrapes.

---

## Prometheus

### Readiness / Health
Prometheus should be reachable and serving its UI once started as part of the full stack.

Typical checks:
- Prometheus process is running
- Targets include the metrics API scrape target
- Queries return non-empty results after the system has traffic

### Verifying Scrape Target
From a high level, you are looking for:
- The metrics API target is **UP**
- Scrape errors are absent (or transient during startup)

If targets are not healthy, check Prometheus logs:

```bash
docker compose logs -f prometheus
```

---

## Grafana

Grafana is provisioned automatically with:
- A Prometheus datasource
- A dashboard: **“Real-time Streaming Analytics — Overview”**

### Health Check
Grafana should report as healthy once started:

```bash
curl -sS http://localhost:3000/api/health
```

If Grafana is not healthy, check logs:

```bash
docker compose logs -f grafana
```

---

## Dashboard Overview

The provisioned Grafana dashboard provides visibility into:

- API request rate (RPS)
- API latency (p95)
- Database connectivity / availability gauge
- Recent stream rows (last 5 minutes)
- Recent donation rows (last 5 minutes)
- Latest window age (seconds)

See `grafana-dashboard.md` for a panel-by-panel guide.

---

## CI Observability Job

In CI, observability is validated independently from the base smoke tests.

The observability job:
- Starts the full stack without running smoke tests automatically
- Verifies Prometheus readiness
- Verifies Grafana health
- Confirms metrics scraping and basic queryability

The entry point used by CI is:

```bash
make full-up RUN_SMOKE=0
```

---

## Troubleshooting

If observability looks wrong:

1. Confirm the API is serving `/prometheus`
   ```bash
   curl -sS http://localhost:8000/prometheus | head
   ```

2. Check Prometheus logs
   ```bash
   docker compose logs -f prometheus
   ```

3. Check Grafana logs / health
   ```bash
   curl -sS http://localhost:3000/api/health
   docker compose logs -f grafana
   ```

4. Run diagnostics
   ```bash
   make doctor
   ```

For deeper debugging, see `troubleshooting.md` and `runbooks.md`.
