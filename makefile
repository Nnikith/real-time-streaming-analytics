init:
	mkdir -p architecture data/raw data/processed services/event-generator services/stream-processor services/metrics-api sql docs
	touch README.md docker-compose.yml .env.example
	touch architecture/architecture.mmd
	touch services/event-generator/requirements.txt services/event-generator/producer.py
	touch services/stream-processor/requirements.txt services/stream-processor/spark_streaming_job.py
	touch services/metrics-api/requirements.txt services/metrics-api/app.py
	touch sql/postgres_init.sql
	touch docs/decisions.md docs/runbook.md
