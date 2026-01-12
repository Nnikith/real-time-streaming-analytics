# Quickstart

This guide gets the **Real-Time Streaming Analytics** stack running locally and verifies that the full pipeline is working end to end.

The system is designed to start reliably with a single command.

---

## Prerequisites

You need the following installed locally:

- Docker
- Docker Compose (v2)
- GNU Make

No additional setup or configuration is required.

---

## Start the Base Pipeline

From the repository root:

```bash
make up
```

This starts the base stack, including:
- Kafka
- Event generator
- Spark Structured Streaming job
- Postgres
- FastAPI metrics API

Containers are started via Docker Compose and may take a short time to become healthy.

---

## Validate the System

Once the stack is running, validate end-to-end behavior:

```bash
make smoke
```

Smoke tests verify that:
- Kafka is available and receiving events
- Spark is running and processing data
- Aggregated rows are written to Postgres
- Donation metrics are computed correctly
- API endpoints respond as expected

Smoke tests are **deterministic** and safe to run multiple times.

---

## Common First-Run Notes

- On the first run, Postgres initializes its schema automatically.
- Spark may take longer to start the first time due to dependency resolution.
- You do not need to create Kafka topics manually.

If smoke tests pass, the pipeline is functioning correctly.

---

## Resetting State (If Needed)

```bash
make reset
```

This removes volumes and re-runs Postgres initialization scripts.

---

## What to Do Next

- Learn how data flows through the system → `architecture.md`
- Understand available `make` commands → `makefile.md`
- Explore metrics and dashboards → `observability.md`
- Diagnose issues → `troubleshooting.md`

---

## Troubleshooting Quickstart Issues

If something fails during startup or smoke tests:

```bash
make doctor
```

For detailed debugging steps, see `troubleshooting.md`.
