# Makefile Reference

This repository uses `make` targets as the primary interface for running, validating, and operating the stack.
All commands below are run from the repository root.

---

## Base vs Full Stack

- **Base stack**: Kafka → Spark → Postgres → FastAPI  
  Started via `make up`

- **Full stack**: Base stack + Prometheus + Grafana  
  Started via `make full-up`

The full stack is enabled by passing `WITH_OBS=1` into the startup scripts.

---

## Start / Stop

### `make up`
Starts the **base** pipeline (no observability).

```bash
make up
```

Notes:
- By default, startup may run smoke tests unless `RUN_SMOKE=0` is set (see “Advanced Options”).

---

### `make down`
Stops the **base** pipeline **without** deleting volumes.

```bash
make down
```

Use when:
- You want to stop containers but keep local state (Postgres data, Spark checkpoints).

---

### `make full-up`
Starts the **full** stack (pipeline + Prometheus + Grafana).

```bash
make full-up
```

---

### `make full-down`
Stops the **full** stack **and deletes volumes** (destructive).

```bash
make full-down
```

This runs the stop script in “wipe volumes” mode and removes local state, including:
- Postgres data volume(s)
- Spark checkpoint/state volumes
- Observability service volumes (if any)

Use when:
- You want to fully tear down the full stack and remove state.

---

## Reset (Destructive)

### `make reset`
Performs a destructive stop (wipe volumes) and then starts the **base** pipeline again.

```bash
make reset
```

Use when:
- You want a clean base stack with reinitialized Postgres schema
- You want to wipe Spark checkpoints/state

---

### `make full-reset`
Performs a destructive stop of the full stack (equivalent to `full-down`), then starts the **full** stack again.

```bash
make full-reset
```

Use when:
- You want a clean full stack (pipeline + observability) from scratch

---

## Smoke Tests

### `make smoke`
Runs deterministic end-to-end smoke tests against the base stack.

```bash
make smoke
```

---

### `make full-smoke`
Runs smoke tests plus observability checks.

```bash
make full-smoke
```

---

## Diagnostics

### `make doctor`
Runs the diagnostic script.

```bash
make doctor
```

---

## Commit Helper

### `make commit`
Runs the repository’s commit helper script.

```bash
make commit
```

Custom message:

```bash
make commit MSG="docs: clarify reset/full-down behavior"
```

---

## Docker Helpers (Read-only)

These are convenience wrappers around `docker compose` for inspecting status and logs.

```bash
make ps
make full-ps
make logs
make full-logs
make logs-spark
make logs-producer
make logs-api
```

---

## Advanced Options

### Skip smoke tests during startup
Some start targets pass `RUN_SMOKE` through to the startup script.

```bash
RUN_SMOKE=0 make up
RUN_SMOKE=0 make full-up
```

### Skip waiting for Prometheus/Grafana readiness during `full-up`
```bash
OBS_WAIT=0 make full-up
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
