# Runbooks

This document contains **step-by-step recovery procedures** for common failure scenarios in the
Real-Time Streaming Analytics system.

Use this when you need a clear sequence of actions to restore the system to a healthy state.

---

## Smoke Tests Failing

### Symptoms
- `make smoke` times out
- Postgres rows are not detected
- API endpoints fail during validation

### Recovery Steps

1. Check overall container status:
   ```bash
   docker compose ps
   ```

2. Inspect Spark logs:
   ```bash
   docker compose logs -f spark-stream
   ```

3. Inspect Kafka / event generator logs:
   ```bash
   docker compose logs -f event-generator
   ```

4. Verify API health:
   ```bash
   curl http://localhost:8000/health
   ```

5. If the issue persists, run diagnostics:
   ```bash
   make doctor
   ```

6. As a last resort, reset state:
   ```bash
   make reset
   ```

---

## Spark Not Producing Rows

### Symptoms
- Spark container is running
- No recent rows appear in Postgres
- Window age increases continuously

### Recovery Steps

1. Check Spark logs for errors:
   ```bash
   docker compose logs -f spark-stream
   ```

2. Look for repeated restarts or checkpoint errors.

3. If Spark is stuck but healthy, restart the base stack:
   ```bash
   make down
   make up
   ```

4. If issues persist, perform a clean reset:
   ```bash
   make reset
   ```

---

## API Unhealthy

### Symptoms
- `/health` returns non-200
- API endpoints fail or time out

### Recovery Steps

1. Check API logs:
   ```bash
   docker compose logs -f metrics-api
   ```

2. Confirm Postgres is reachable:
   ```bash
   docker compose logs -f postgres
   ```

3. Restart the base stack:
   ```bash
   make down
   make up
   ```

---

## Prometheus or Grafana Issues

### Symptoms
- Prometheus targets are DOWN
- Grafana dashboard shows no data

### Recovery Steps

1. Confirm the metrics endpoint:
   ```bash
   curl http://localhost:8000/prometheus | head
   ```

2. Check Prometheus logs:
   ```bash
   docker compose logs -f prometheus
   ```

3. Check Grafana health:
   ```bash
   curl http://localhost:3000/api/health
   ```

4. Restart the full stack if needed:
   ```bash
   make full-down
   make full-up
   ```

---

## When Nothing Else Works

Perform a full reset of the stack:

```bash
make full-reset
```

This wipes all local state and reinitializes the system from scratch.

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
