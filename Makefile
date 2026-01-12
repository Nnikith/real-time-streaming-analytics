.PHONY: \
	up down full-up full-down reset full-reset \
	smoke full-smoke doctor commit \
	ps full-ps logs full-logs \
	logs-spark logs-producer logs-api help

# Defaults
OBS_WAIT ?= 1
RUN_SMOKE ?= 1

# Compose commands
DC_BASE = docker compose -f docker-compose.yml
DC_FULL = docker compose -f docker-compose.yml -f docker-compose.observability.yml


# ------------------------------------------------------------------------------
# Start / Stop
# ------------------------------------------------------------------------------

up:
	@RUN_SMOKE=$(RUN_SMOKE) bash scripts/start.sh

down:
	@bash scripts/stop.sh

full-up:
	@WITH_OBS=1 OBS_WAIT=$(OBS_WAIT) RUN_SMOKE=$(RUN_SMOKE) bash scripts/start.sh

full-down:
	@WITH_OBS=1 bash scripts/stop.sh no


# ------------------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------------------

reset:
	@RUN_SMOKE=$(RUN_SMOKE) bash scripts/reset.sh

full-reset:
	@WITH_OBS=1 OBS_WAIT=$(OBS_WAIT) RUN_SMOKE=$(RUN_SMOKE) bash scripts/reset.sh


# ------------------------------------------------------------------------------
# Smoke tests
# ------------------------------------------------------------------------------

smoke:
	@bash scripts/smoke.sh

full-smoke:
	@WITH_OBS=1 CHECK_OBS=1 bash scripts/smoke.sh


# ------------------------------------------------------------------------------
# Diagnostics / Utilities
# ------------------------------------------------------------------------------

doctor:
	@bash scripts/doctor.sh

commit:
	@bash scripts/git_commit.sh $(MSG)


# ------------------------------------------------------------------------------
# Docker compose helpers (read-only)
# ------------------------------------------------------------------------------

ps:
	@$(DC_BASE) ps

full-ps:
	@$(DC_FULL) ps

logs:
	@$(DC_BASE) logs -f

full-logs:
	@$(DC_FULL) logs -f

logs-spark:
	@$(DC_BASE) logs -f spark-stream

logs-producer:
	@$(DC_BASE) logs -f event-generator

logs-api:
	@$(DC_BASE) logs -f metrics-api


# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------

help:
	@echo ""
	@echo "🚀 Start / Stop"
	@echo "  make up                 Start base pipeline"
	@echo "  make down               Stop base pipeline (keep volumes)"
	@echo "  make full-up            Start pipeline + Prometheus + Grafana"
	@echo "  make full-down          Stop full pipeline + delete volumes"
	@echo ""
	@echo "♻️ Reset"
	@echo "  make reset              Wipe volumes + restart base pipeline"
	@echo "  make full-reset         Wipe volumes + restart full pipeline (obs)"
	@echo ""
	@echo "🧪 Testing"
	@echo "  make smoke              Run base smoke tests"
	@echo "  make full-smoke         Run smoke + observability checks"
	@echo ""
	@echo "🛠  Diagnostics"
	@echo "  make doctor             Run diagnostics"
	@echo ""
	@echo "📦 Docker helpers"
	@echo "  make ps                 docker compose ps (base)"
	@echo "  make full-ps            docker compose ps (with observability)"
	@echo "  make logs               Follow logs (base)"
	@echo "  make full-logs          Follow logs (with observability)"
	@echo ""
	@echo "⚙️  Advanced"
	@echo "  OBS_WAIT=0 make full-up Skip waiting for Prometheus/Grafana"
	@echo "  RUN_SMOKE=0 make up     Skip smoke tests"
	@echo ""
