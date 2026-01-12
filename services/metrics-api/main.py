import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="metrics-api")


# -----------------------------------------------------------------------------
# Prometheus metrics
# -----------------------------------------------------------------------------
API_HTTP_REQUESTS_TOTAL = Counter(
    "api_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

API_HTTP_REQUEST_DURATION = Histogram(
    "api_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

API_DB_OK = Gauge("api_db_ok", "Database connectivity ok (1) or error (0)")
API_STREAM_METRICS_ROWS_RECENT = Gauge(
    "api_stream_metrics_rows_recent",
    "Number of stream_metrics_minute rows in last 5 minutes",
)
API_DONATION_ROWS_RECENT = Gauge(
    "api_donation_rows_recent",
    "Number of rows with donations_usd > 0 in last 5 minutes",
)
API_LATEST_WINDOW_AGE_SECONDS = Gauge(
    "api_latest_window_age_seconds",
    "Age in seconds of the most recent window_start",
)


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
def _get_db_conn():
    """
    Supports either DATABASE_URL or PG* env vars.
    Defaults match the typical docker-compose setup:
      host=postgres db=realtime user=rt password=rt
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

    host = os.getenv("PGHOST", "postgres")
    port = int(os.getenv("PGPORT", "5432"))
    db = os.getenv("PGDATABASE", "realtime")
    user = os.getenv("PGUSER", "rt")
    password = os.getenv("PGPASSWORD", "rt")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
        cursor_factory=RealDictCursor,
    )


def _db_scalar(query: str, params: Optional[tuple] = None) -> Any:
    conn = _get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
            if not row:
                return None
            # RealDictCursor gives dict rows
            return next(iter(row.values()))
    finally:
        conn.close()


def _db_rows(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    conn = _get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return rows or []
    finally:
        conn.close()


def _iso(dt: Any) -> Any:
    """Convert datetime to ISO string; passthrough otherwise."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


# -----------------------------------------------------------------------------
# Middleware (Counter + Histogram)
# -----------------------------------------------------------------------------
@app.middleware("http")
async def prometheus_http_middleware(request: Request, call_next):
    start = time.perf_counter()

    response: Response
    status_code: int = 500
    path_label = request.url.path

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        # Normalize path to route template when possible (reduces cardinality)
        try:
            route = request.scope.get("route")
            if route and hasattr(route, "path"):
                path_label = route.path  # e.g., "/metrics/latest"
        except Exception:
            pass

        duration = time.perf_counter() - start
        API_HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            path=path_label,
            status=str(status_code),
        ).inc()
        API_HTTP_REQUEST_DURATION.labels(
            method=request.method,
            path=path_label,
        ).observe(duration)


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    # Basic DB ping
    try:
        _db_scalar("SELECT 1;")
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=503, content={"ok": False, "error": str(e)})


@app.get("/metrics")
def metrics_summary():
    """
    JSON summary endpoint.
    Smoke-test contract requires:
      - "rows"
      - "latest_window_start"
    """
    try:
        latest_window_start = _db_scalar(
            "SELECT MAX(window_start) FROM stream_metrics_minute;"
        )
        latest = _db_rows(
            """
            SELECT window_start, stream_id, active_viewers, donations_usd
            FROM stream_metrics_minute
            ORDER BY window_start DESC
            LIMIT 100;
            """
        )

        latest_window_start = _iso(latest_window_start)
        for r in latest:
            r["window_start"] = _iso(r.get("window_start"))

        return {
            "latest_window_start": latest_window_start,
            "rows": latest,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/metrics/latest")
def metrics_latest():
    """
    Returns the most recent minute window per stream.
    """
    try:
        rows = _db_rows(
            """
            SELECT DISTINCT ON (stream_id)
              stream_id,
              window_start,
              active_viewers,
              donations_usd
            FROM stream_metrics_minute
            ORDER BY stream_id, window_start DESC;
            """
        )
        for r in rows:
            r["window_start"] = _iso(r.get("window_start"))
        return {"rows": rows}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/streams/top")
def streams_top(limit: int = 10):
    """
    Top streams by most recent active_viewers.
    """
    try:
        rows = _db_rows(
            """
            SELECT DISTINCT ON (stream_id)
              stream_id,
              window_start,
              active_viewers,
              donations_usd
            FROM stream_metrics_minute
            ORDER BY stream_id, window_start DESC;
            """
        )
        for r in rows:
            r["window_start"] = _iso(r.get("window_start"))

        rows_sorted = sorted(rows, key=lambda r: (r.get("active_viewers") or 0), reverse=True)
        return {"rows": rows_sorted[: max(1, min(limit, 100))]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# -----------------------------------------------------------------------------
# /prometheus endpoint (scrape)
# -----------------------------------------------------------------------------
@app.get("/prometheus")
def prometheus_scrape():
    """
    Compute gauges at scrape time, then return Prometheus exposition format.
    """
    db_ok = 0
    try:
        _db_scalar("SELECT 1;")
        db_ok = 1
    except Exception:
        db_ok = 0

    API_DB_OK.set(db_ok)

    if db_ok == 1:
        try:
            # Rows in last 5 minutes
            recent_rows = _db_scalar(
                """
                SELECT COUNT(*)::bigint
                FROM stream_metrics_minute
                WHERE window_start >= NOW() - interval '5 minutes';
                """
            )
            API_STREAM_METRICS_ROWS_RECENT.set(float(recent_rows or 0))

            donation_rows = _db_scalar(
                """
                SELECT COUNT(*)::bigint
                FROM stream_metrics_minute
                WHERE window_start >= NOW() - interval '5 minutes'
                  AND donations_usd > 0;
                """
            )
            API_DONATION_ROWS_RECENT.set(float(donation_rows or 0))

            # Latest window age
            latest_window = _db_scalar(
                """
                SELECT EXTRACT(EPOCH FROM (NOW() - MAX(window_start)))::double precision
                FROM stream_metrics_minute;
                """
            )
            API_LATEST_WINDOW_AGE_SECONDS.set(float(latest_window or 0.0))
        except Exception:
            # Degrade gracefully; still return whatever we have
            pass

    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
