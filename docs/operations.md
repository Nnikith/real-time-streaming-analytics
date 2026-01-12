# Operations

This document covers operational workflows for running the Real-Time Streaming Analytics system locally and in CI.

---

## Base vs Full Stack

- **Base stack**: Kafka → Spark → Postgres → FastAPI  
  Use for development and base smoke tests.

- **Full stack**: Base stack + Prometheus + Grafana  
  Use when validating observability and dashboards.

---

## Start / Stop

### Start base stack
```bash
make up
```

### Stop base stack (keep volumes)
```bash
make down
```

`make down` stops containers but preserves local state such as Postgres data and Spark checkpoints.

---

### Start full stack (includes Prometheus + Grafana)
```bash
make full-up
```

### Stop full stack (delete volumes — destructive)
```bash
make full-down
```

`make full-down` stops the full stack and removes volumes (local state is deleted).

---

## Resetting State (Destructive)

### Reset base stack
```bash
make reset
```

`make reset` wipes volumes (Postgres data + Spark checkpoints/state) and then starts the **base** stack again.

---

### Reset full stack
```bash
make full-reset
```

`make full-reset` wipes volumes for the **full** stack and then starts the full stack again (including observability).

---

## When to Use What

| Goal | Command |
|------|---------|
| Start base pipeline | `make up` |
| Stop base pipeline, keep data | `make down` |
| Start full pipeline + observability | `make full-up` |
| Stop full pipeline and wipe state | `make full-down` |
| Wipe base state and restart base | `make reset` |
| Wipe full state and restart full | `make full-reset` |

---

## Diagnostics

If something behaves unexpectedly:

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

