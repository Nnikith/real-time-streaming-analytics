# 📘 Runbook

Operational guide for running and debugging the pipeline.

---

## ▶️ Starting the system
```bash
make up
```

---

## 🧪 Validating the system
```bash
make smoke
```

---

## ♻️ Full reset
```bash
make reset
```

---

## 🚨 Debugging

### Kafka
```bash
docker compose logs -f event-generator
```

### Spark
```bash
docker compose logs -f spark-stream
```

### Postgres
```bash
docker exec -it $(docker compose ps -q postgres) psql -U rt -d realtime
```

---

## 🩺 Doctor script
```bash
bash scripts/doctor.sh
```
