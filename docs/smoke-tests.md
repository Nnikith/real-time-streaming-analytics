# Smoke Tests

Smoke tests validate the pipeline **end to end** and are intended to be **deterministic**.
They confirm that Kafka ingestion, Spark processing, Postgres writes, and API queries are all functioning.

---

## Run

From the repository root:

```bash
make smoke
```

To run smoke tests against the full (observability) stack:

```bash
make full-smoke
```

---

## What Smoke Tests Validate

Smoke tests are designed to confirm the following behaviors:

- **Kafka is reachable** and receiving events from the event generator
- **Spark Structured Streaming is healthy** and actively processing data
- **Postgres is reachable** and contains **recent aggregated rows**
- **Minute-window stream metrics are written** (Spark → Postgres)
- **Donations aggregation works** (donations roll up correctly)
- **FastAPI endpoints respond** with expected status codes and payload shape

> Smoke tests are safe to run multiple times. They do not require a clean database to pass.

---

## What “Pass” Looks Like

A successful smoke run indicates:

- The base stack started correctly (`make up`)
- Spark has produced at least one recent minute window
- Postgres contains rows for recent windows (within the test’s wait time)
- The API is responding and can query the stored aggregates

If smoke tests pass, the pipeline is functioning end to end.

---

## Common Failures and Fast Checks

### Smoke times out waiting for Postgres rows
This usually means Spark has not written recent windows yet.

Fast checks:

```bash
docker compose logs -f spark-stream
```

Confirm Spark is running and not repeatedly restarting.

---

### API is up but endpoints fail
Check API logs:

```bash
docker compose logs -f metrics-api
```

Then verify health directly:

```bash
curl -sS http://localhost:8000/health
```

---

### Kafka-related failures
Check the producer (event generator) logs:

```bash
docker compose logs -f event-generator
```

If Kafka is unhealthy, it will typically show up as connection errors or repeated retries.

---

## Diagnostics

If smoke fails and the cause is not obvious, run the diagnostic script:

```bash
make doctor
```

This performs a cross-service readiness and connectivity check and is the fastest way to narrow down where the failure is occurring.

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

