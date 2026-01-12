# Grafana Dashboard Guide

This document explains the intent and interpretation of the pre-provisioned Grafana dashboard:

**“Real-time Streaming Analytics — Overview”**

The dashboard provides a high-level view of pipeline health, data freshness, and API performance.

---

## Dashboard Scope

The dashboard is designed to answer the following questions:

- Is the pipeline currently healthy?
- Is data flowing end to end?
- Are aggregations recent?
- Is the API responsive?
- Is Postgres reachable?

It is not intended for deep debugging or ad-hoc analysis.

---

## Panels and Interpretation

### API RPS
Shows the request rate handled by the FastAPI service.

**What to expect:**
- Non-zero traffic once smoke tests or manual queries run
- Spikes during smoke tests or CI validation

**Red flags:**
- Flatline at zero while queries are being made

---

### API p95 Latency
Shows the 95th percentile request latency for API endpoints.

**What to expect:**
- Low, stable latency under normal operation
- Temporary spikes during startup or resets

**Red flags:**
- Sustained high latency
- Sudden increases without traffic changes

---

### DB OK Gauge
Indicates whether the API can successfully query Postgres.

**What to expect:**
- “OK” during normal operation

**Red flags:**
- Not OK, which usually indicates Postgres connectivity issues

---

### Stream Rows (Last 5 Minutes)
Shows the number of aggregated stream metric rows written recently.

**What to expect:**
- Continuous updates as Spark processes events
- Values reflecting recent minute windows

**Red flags:**
- No recent rows despite Spark running

---

### Donation Rows (Last 5 Minutes)
Shows donation aggregation rows written recently.

**What to expect:**
- Values aligned with stream activity
- Fewer rows than total stream rows, depending on data

**Red flags:**
- Missing rows while stream rows are present

---

### Latest Window Age (Seconds)
Shows how old the most recent aggregated window is.

**What to expect:**
- Low values (near real time) under normal operation

**Red flags:**
- Large or steadily increasing values, indicating stalled processing

---

## When the Dashboard Looks Wrong

If one or more panels look incorrect:

1. Confirm the pipeline is running
   ```bash
   make ps
   ```

2. Check Spark logs
   ```bash
   docker compose logs -f spark-stream
   ```

3. Verify API health
   ```bash
   curl http://localhost:8000/health
   ```

4. Run diagnostics
   ```bash
   make doctor
   ```

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
