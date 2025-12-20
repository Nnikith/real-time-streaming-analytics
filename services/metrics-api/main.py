import os
from datetime import datetime, timezone
from typing import Literal, Optional, Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(title="Real-Time Streaming Analytics Metrics API")

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "realtime")
PG_USER = os.getenv("PG_USER", "rt")
PG_PASS = os.getenv("PG_PASS", "rt")
PG_TABLE = os.getenv("PG_TABLE", "stream_metrics_minute")


def pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        cursor_factory=RealDictCursor,
    )


def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


@app.get("/health")
def health():
    # Basic connectivity check
    try:
        one = fetch_one("SELECT 1 AS ok;")
        return {"ok": True, "db": bool(one and one.get("ok") == 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/metrics")
def metrics(
    stream_id: Optional[str] = Query(default=None, description="Filter metrics by stream_id"),
    minutes: int = Query(default=60, ge=1, le=24 * 60, description="Lookback window in minutes"),
    limit: int = Query(default=200, ge=1, le=5000, description="Max rows returned"),
    order_by: Literal["window_start", "donations_usd", "chat_messages", "active_viewers"] = Query(
        default="window_start", description="Sort column"
    ),
    direction: Literal["asc", "desc"] = Query(default="desc", description="Sort direction"),
):
    # Build safe ORDER BY
    allowed = {"window_start", "donations_usd", "chat_messages", "active_viewers"}
    if order_by not in allowed:
        raise HTTPException(status_code=400, detail="Invalid order_by")
    if direction not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid direction")

    where = "WHERE window_start > NOW() - (%s || ' minutes')::interval"
    params: List[Any] = [minutes]

    if stream_id:
        where += " AND stream_id = %s"
        params.append(stream_id)

    sql = f"""
      SELECT window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd
      FROM {PG_TABLE}
      {where}
      ORDER BY {order_by} {direction}
      LIMIT %s
    """
    params.append(limit)

    rows = fetch_all(sql, tuple(params))

    latest = None
    if rows:
        # latest window_start among returned rows (not necessarily newest if sorting by another column)
        latest = max(r["window_start"] for r in rows)

    return {
        "rows": rows,
        "latest_window_start": latest,
        "filters": {
            "stream_id": stream_id,
            "minutes": minutes,
            "limit": limit,
            "order_by": order_by,
            "direction": direction,
        },
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics/latest")
def metrics_latest(
    stream_id: Optional[str] = Query(default=None),
):
    # “Latest complete window”: choose max(window_start) where window_end <= now()
    # This avoids a partially-updating current minute.
    where = "WHERE window_end <= NOW()"
    params: List[Any] = []

    if stream_id:
        where += " AND stream_id = %s"
        params.append(stream_id)

    row = fetch_one(
        f"""
        SELECT window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd
        FROM {PG_TABLE}
        {where}
        ORDER BY window_start DESC
        LIMIT 1
        """,
        tuple(params),
    )

    return {"row": row, "server_time_utc": datetime.now(timezone.utc).isoformat()}


@app.get("/streams")
def streams(
    minutes: int = Query(default=120, ge=1, le=24 * 60),
    limit: int = Query(default=200, ge=1, le=5000),
):
    rows = fetch_all(
        f"""
        SELECT stream_id, MAX(window_start) AS last_seen
        FROM {PG_TABLE}
        WHERE window_start > NOW() - (%s || ' minutes')::interval
        GROUP BY stream_id
        ORDER BY last_seen DESC
        LIMIT %s
        """,
        (minutes, limit),
    )
    return {"rows": rows, "server_time_utc": datetime.now(timezone.utc).isoformat()}


@app.get("/streams/top")
def streams_top(
    minutes: int = Query(default=10, ge=1, le=24 * 60),
    n: int = Query(default=10, ge=1, le=200),
    by: Literal["active_viewers", "chat_messages", "donations_usd"] = Query(default="donations_usd"),
):
    # Aggregate over last N minutes.
    # For active_viewers, taking MAX is more meaningful than SUM.
    if by == "active_viewers":
        agg = "MAX(active_viewers) AS value"
    elif by == "chat_messages":
        agg = "SUM(chat_messages) AS value"
    else:
        agg = "ROUND(SUM(donations_usd)::numeric, 2) AS value"


    rows = fetch_all(
        f"""
        SELECT stream_id, {agg}
        FROM {PG_TABLE}
        WHERE window_start > NOW() - (%s || ' minutes')::interval
        GROUP BY stream_id
        ORDER BY value DESC NULLS LAST
        LIMIT %s
        """,
        (minutes, n),
    )

    return {
        "rows": rows,
        "by": by,
        "minutes": minutes,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
    }
