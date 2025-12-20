.PHONY: up down reset smoke commit help full-down ps logs logs-spark logs-producer logs-api doctor

up:
	@bash scripts/start.sh

down:
	@bash scripts/stop.sh

full-down:
	@bash scripts/stop.sh no

reset:
	@bash scripts/reset.sh

smoke:
	@bash scripts/smoke.sh

doctor:
	@bash scripts/doctor.sh

commit:
	@bash scripts/git_commit.sh $(MSG)

ps:
	@docker compose ps

logs:
	@docker compose logs -f

logs-spark:
	@docker compose logs -f spark-stream

logs-producer:
	@docker compose logs -f event-generator

logs-api:
	@docker compose logs -f metrics-api

help:
	@echo "Available commands:"
	@echo "  make up            Start full pipeline"
	@echo "  make down          Stop pipeline"
	@echo "  make full-down     Stop pipeline and deletes Postgres data + checkpoints"
	@echo "  make reset         Clean state + restart"
	@echo "  make smoke         Run smoke tests"
	@echo "  make commit        Interactive git commit"
	@echo "  make ps            Docker compose status"
	@echo "  make logs          Follow all logs"
	@echo "  make logs-spark    Follow Spark logs"
	@echo "  make logs-producer Follow producer logs"
	@echo "  make logs-api      Follow API logs"
