# Troubleshooting

This document helps diagnose common issues when running the **Real-Time Streaming Analytics** system.

It is organized by symptom rather than component.

---

## Smoke Tests Fail

### Smoke tests time out waiting for Postgres rows

Likely causes:
- Spark has not started processing yet
- Spark is repeatedly restarting
- Kafka is unavailable

Checks:
```bash
docker compose logs -f spark-stream
docker compose logs -f event-generator
```

Confirm Spark is running and not crashing.

---

### API endpoints fail during smoke tests

Checks:
```bash
docker compose logs -f metrics-api
curl http://localhost:8000/health
```

If `/health` fails, the API is not ready or cannot reach Postgres.

---

## No Recent Data Appearing

### Stream rows missing

Checks:
```bash
docker compose logs -f spark-stream
```

Confirm that:
- Spark is reading from Kafka
- Windows are advancing
- No repeated checkpoint or permission errors are present

---

### Donation rows missing

If stream rows exist but donation rows do not:
- Confirm Spark is running donation aggregation logic
- Check Spark logs for aggregation errors

---

## Observability Issues

### Prometheus not scraping metrics

Checks:
```bash
curl http://localhost:8000/prometheus | head
docker compose logs -f prometheus
```

Confirm the metrics endpoint is reachable and the target is marked UP.

---

### Grafana dashboard is empty

Checks:
```bash
curl http://localhost:3000/api/health
docker compose logs -f grafana
```

If Grafana is healthy but panels are empty:
- Confirm Prometheus has data
- Check time range and dashboard refresh

---

## Containers Restarting Repeatedly

Checks:
```bash
docker compose ps
docker compose logs <service>
```

Repeated restarts usually indicate:
- Startup failures
- Configuration or permission issues
- Resource constraints

---

## When in Doubt

Run diagnostics:

```bash
make doctor
```

The doctor script performs cross-service checks and highlights common failure modes.

---

## Additional Documentation

- Back to repository root: [`README.md`](../README.md)
- How to run the system: [`quickstart.md`](quickstart.md)
- Architecture and data flow: [`architecture.md`](architecture.md)
- Design decisions: [`decisions.md`](decisions.md)
- Make targets and workflows: [`makefile.md`](makefile.md)
- Smoke test validation: [`smoke-tests.md`](smoke-tests.md)
- Observability details: [`observability.md`](observability.md)
- Grafana dashboard guide: [`grafana-dashboard.md`](grafana-dashboard.md)
- Operations and lifecycle: [`operations.md`](operations.md)
- Troubleshooting steps: [`troubleshooting.md`](troubleshooting.md)
- Recovery procedures: [`runbooks.md`](runbooks.md)
- Terminology reference: [`glossary.md`](glossary.md)

