# Scripts

These scripts give you **one-command startup**, **end-to-end smoke tests**, and **clean stop/reset** for the pipeline.

## One-time setup

From repo root:

```bash
chmod +x scripts/*.sh
```

## Start everything (runs smoke tests automatically)

```bash
bash scripts/start.sh
```

## Stop everything (keep volumes)

```bash
bash scripts/stop.sh
```

## Stop everything (wipe volumes)

> This will reset Postgres data + Spark checkpoints.

```bash
bash scripts/stop.sh no
```

## Full reset (wipe + start + smoke tests)

```bash
bash scripts/reset.sh
```

## Smoke tests only

```bash
bash scripts/smoke.sh
```

## Makefile shortcuts

```bash
make up
make down
make reset
make smoke
make logs
```

## What the smoke tests validate

- Kafka topic exists
- Producer is publishing (offsets advance)
- Spark writes aggregated rows to Postgres
- Metrics API `/health` and `/metrics` respond with expected JSON shape
