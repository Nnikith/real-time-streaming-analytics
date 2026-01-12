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

## Related Documentation

- Make targets reference: `makefile.md`
- Smoke test behavior: `smoke-tests.md`
- Troubleshooting: `troubleshooting.md`
- Recovery procedures: `runbooks.md`
