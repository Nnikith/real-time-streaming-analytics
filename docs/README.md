# Documentation Index

This directory contains all **project documentation** for the  
**Real-Time Streaming Analytics** pipeline.

The codebase is feature-complete and stable.  
These documents focus on **understanding, operating, and troubleshooting** the system.

---

## 📌 Where to Start

If you are new to the repository:

1. **Quickstart**  
   👉 `quickstart.md`  
   How to run the stack locally and verify it works.

2. **Architecture**  
   👉 `architecture.md`  
   End-to-end data flow and component responsibilities.

3. **Makefile Reference**  
   👉 `makefile.md`  
   What each `make` command does and when to use it.

---

## 🧪 Testing & Validation

- **Smoke Tests**  
  👉 `smoke-tests.md`  
  What `make smoke` validates and how to debug failures.

- **Runbooks**  
  👉 `runbooks.md`  
  Step-by-step procedures for common failure scenarios.

---

## 📊 Observability

- **Observability Overview**  
  👉 `observability.md`  
  Metrics pipeline, Prometheus scraping, and health checks.

- **Grafana Dashboard Guide**  
  👉 `grafana-dashboard.md`  
  How to read and interpret the provided dashboard.

---

## 🛠️ Operations

- **Operations Guide**  
  👉 `operations.md`  
  Day-2 operations, resets, and local vs CI usage.

- **Troubleshooting**  
  👉 `troubleshooting.md`  
  Diagnosing common issues across Spark, Postgres, API, and observability.

---

## 📖 Reference

- **Glossary** (optional)  
  👉 `glossary.md`  
  Project-specific terms and definitions.

---

## Scope Notes

- Spark jobs, API logic, metrics, Dockerfiles, and dashboards are **out of scope**
- Documentation reflects **current, working behavior**
- No code changes are described or implied

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
