# 🧠 Architecture Decisions

Why specific design choices were made.

---

## Kafka
Durable event log, decouples producers and consumers.

## Spark Structured Streaming
Windowing, watermarking, checkpointing.

## Postgres
UPSERT-safe relational storage.

## FastAPI
Fast, typed, minimal overhead.

## Smoke Tests
End-to-end correctness guarantees.

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
