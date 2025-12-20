#!/usr/bin/env bash
set -euo pipefail

# -------- Logging helpers --------
log()  { echo -e "✅ $*"; }
info() { echo -e "ℹ️  $*"; }
warn() { echo -e "⚠️  $*"; }
err()  { echo -e "❌ $*" >&2; }

# -------- Small utilities --------
need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { err "Missing required command: $1"; exit 1; }
}

# Wait until a command succeeds (with timeout)
wait_until() {
  local desc="$1"
  local timeout="${2:-60}"
  shift 2
  local start now

  start="$(date +%s)"
  info "Waiting up to ${timeout}s: ${desc}"

  while true; do
    if "$@" >/dev/null 2>&1; then
      log "${desc}"
      return 0
    fi
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      err "Timeout waiting for: ${desc}"
      return 1
    fi
    sleep 2
  done
}

# Same, but prints one-line progress dots
wait_until_dots() {
  local desc="$1"
  local timeout="${2:-60}"
  shift 2
  local start now

  start="$(date +%s)"
  info "Waiting up to ${timeout}s: ${desc}"
  while true; do
    if "$@" >/dev/null 2>&1; then
      echo
      log "${desc}"
      return 0
    fi
    echo -n "."
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      echo
      err "Timeout waiting for: ${desc}"
      return 1
    fi
    sleep 2
  done
}

# Convenience: run a command inside kafka container
kafka_exec() {
  docker exec -i real-time-streaming-analytics-kafka-1 bash -lc "$*"
}

# Convenience: run psql inside postgres container
pg_exec() {
  docker exec -i real-time-streaming-analytics-postgres-1 bash -lc "$*"
}
