import os
from typing import Optional, Literal, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException


# -----------------------------
# Config
# -----------------------------
APP_NAME = os.getenv("APP_NAME", "metrics-api")

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "realtime")
PG_USER = os.getenv("PG_USER", "rt")
PG_PASSWORD = os.getenv("PG_PASSWORD", "rt")

PG_METRICS_TABLE = os.getenv("PG_METRICS_TABLE", "stream_metrics_minute")
PG_STATE_TABLE = os.getenv("PG_STATE_TABLE", "stream_state")

# Optional: DATABASE_URL overrides individual PG_* vars
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql://rt:rt@postgres:5432/realtime


# -----------------------------
# App
# -----------------------------
app = FastAPI(title=APP_NAME)


def _is_safe_ident(name: str) -> bool:
    """
    Minimal identifier allowlist:
    - letters, digits, underscore
    - must start with letter/underscore
    """
    if not name:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    for ch in name:
        if not (ch.isalnum() or ch == "_"):
            return False
    return True


def _safe_table(name: str) -> str:
    if not _is_safe_ident(name):
        raise ValueError(f"Unsafe table name: {name!r}")
    return name


SAFE_METRICS_TABLE = _safe_table(PG_METRICS_TABLE)
SAFE_STATE_TABLE = _safe_table(PG_STATE_TABLE)


def get_conn():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )


def _fetchone_dict(cur) -> Dict[str, Any]:
    row = cur.fetchone()
    return dict(row) if row else {}


def _to_iso(obj):
    # psycopg2 returns datetime objects for timestamptz/timestamp; FastAPI can serialize,
    # but we’ll normalize to ISO strings for consistent output.
    if obj is None:
        return None
    try:
        return obj.isoformat()
    except Exception:
        return str(obj)


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/state")
def state():
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT stream_id, active_viewers, updated_at
                    FROM {SAFE_STATE_TABLE}
                    ORDER BY updated_at DESC, stream_id;
                """)
                rows = cur.fetchall()
                for r in rows:
                    r["updated_at"] = _to_iso(r.get("updated_at"))
                return {"streams": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/latest")
def latest_metrics(
    stream_id: Optional[str] = Query(None, description="Filter to a single stream_id (e.g., stream_1002)")
):
    """
    Latest window metrics (for all streams or one stream).
    """
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT MAX(window_start) AS latest FROM {SAFE_METRICS_TABLE};")
                latest = _fetchone_dict(cur).get("latest")

                if latest is None:
                    return {"latest_window_start": None, "rows": []}

                if stream_id:
                    cur.execute(f"""
                        SELECT window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd
                        FROM {SAFE_METRICS_TABLE}
                        WHERE window_start = %s AND stream_id = %s
                        ORDER BY stream_id;
                    """, (latest, stream_id))
                else:
                    cur.execute(f"""
                        SELECT window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd
                        FROM {SAFE_METRICS_TABLE}
                        WHERE window_start = %s
                        ORDER BY stream_id;
                    """, (latest,))

                rows = cur.fetchall()
                for r in rows:
                    r["window_start"] = _to_iso(r.get("window_start"))
                    r["window_end"] = _to_iso(r.get("window_end"))

                return {"latest_window_start": _to_iso(latest), "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def metrics_history(
    minutes: int = Query(15, ge=1, le=24 * 60, description="How many minutes of history to return"),
    stream_id: Optional[str] = Query(None, description="Filter to a single stream_id"),
):
    """
    History endpoint.
    Returns all rows from the last N minutes (by window_start) for all streams or one stream.
    """
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Use latest window_start as an anchor to make "last N minutes" stable.
                cur.execute(f"SELECT MAX(window_start) AS latest FROM {SAFE_METRICS_TABLE};")
                latest = _fetchone_dict(cur).get("latest")
                if latest is None:
                    return {"latest_window_start": None, "minutes": minutes, "rows": []}

                if stream_id:
                    cur.execute(f"""
                        SELECT window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd
                        FROM {SAFE_METRICS_TABLE}
                        WHERE stream_id = %s
                          AND window_start >= (%s::timestamp - (%s || ' minutes')::interval)
                          AND window_start <= %s
                        ORDER BY window_start DESC, stream_id;
                    """, (stream_id, latest, minutes, latest))
                else:
                    cur.execute(f"""
                        SELECT window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd
                        FROM {SAFE_METRICS_TABLE}
                        WHERE window_start >= (%s::timestamp - (%s || ' minutes')::interval)
                          AND window_start <= %s
                        ORDER BY window_start DESC, stream_id;
                    """, (latest, minutes, latest))

                rows = cur.fetchall()
                for r in rows:
                    r["window_start"] = _to_iso(r.get("window_start"))
                    r["window_end"] = _to_iso(r.get("window_end"))

                return {"latest_window_start": _to_iso(latest), "minutes": minutes, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/top")
def top_streams(
    by: Literal["viewers", "chat", "donations"] = "donations",
    limit: int = Query(3, ge=1, le=50),
):
    """
    Top streams for the latest window by viewers/chat/donations.
    """
    order_expr = {
        "viewers": "active_viewers DESC",
        "chat": "chat_messages DESC",
        "donations": "donations_usd DESC",
    }[by]

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT MAX(window_start) AS latest FROM {SAFE_METRICS_TABLE};")
                latest = _fetchone_dict(cur).get("latest")
                if latest is None:
                    return {"latest_window_start": None, "by": by, "rows": []}

                cur.execute(f"""
                    SELECT window_start, stream_id, active_viewers, chat_messages, donations_usd
                    FROM {SAFE_METRICS_TABLE}
                    WHERE window_start = %s
                    ORDER BY {order_expr}
                    LIMIT %s;
                """, (latest, limit))

                rows = cur.fetchall()
                for r in rows:
                    r["window_start"] = _to_iso(r.get("window_start"))

                return {"latest_window_start": _to_iso(latest), "by": by, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
