# Glossary

Project-specific terms used in this repository and its documentation.

---

## Base stack
The core pipeline services started by `make up` (Kafka → Spark → Postgres → FastAPI).

---

## Full stack
The base stack plus observability services (Prometheus and Grafana), started by `make full-up`.

---

## Event generator
A service that continuously produces JSON events into Kafka to drive the pipeline and support deterministic validation.

---

## Minute window
A fixed, minute-based aggregation interval used by Spark Structured Streaming to compute per-minute metrics.

---

## Upsert
A database write pattern that inserts a row if it does not exist, or updates it if it does. Used to make writes restart-safe.

---

## Checkpoint
Structured Streaming state stored by Spark to track progress and ensure restart safety.

---

## Smoke tests
Deterministic end-to-end validation run via `make smoke` (or `make full-smoke` for the full stack).

---

## Window age
A freshness indicator that describes how old the most recent aggregated window is (typically visualized in Grafana).

---

## Metrics API
The FastAPI service that queries Postgres for aggregated results and exposes:
- JSON query endpoints (e.g., `/metrics`, `/streams/top`)
- Prometheus scrape endpoint (`/prometheus`)
