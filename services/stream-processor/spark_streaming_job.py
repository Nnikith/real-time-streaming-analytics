import os
import sys
from typing import Optional

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType
)

# -----------------------------
# Config (env overrides)
# -----------------------------
APP_NAME = os.getenv("SPARK_APP_NAME", "realtime-stream-analytics")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "stream.events")
KAFKA_STARTING_OFFSETS = os.getenv("KAFKA_STARTING_OFFSETS", "latest")  # earliest|latest

WATERMARK_DELAY = os.getenv("WATERMARK_DELAY", "10 minutes")
WINDOW_DURATION = os.getenv("WINDOW_DURATION", "1 minute")
TRIGGER_INTERVAL = os.getenv("TRIGGER_INTERVAL", "10 seconds")

# IMPORTANT: checkpoint per query
CHECKPOINT_ROOT = os.getenv("CHECKPOINT_ROOT", "/tmp/checkpoints")
CHECKPOINT_METRICS = os.getenv("CHECKPOINT_METRICS", f"{CHECKPOINT_ROOT}/stream_metrics_minute")

# Postgres
PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "realtime")
PG_USER = os.getenv("PG_USER", "rt")
PG_PASSWORD = os.getenv("PG_PASSWORD", "rt")

# Table names
PG_METRICS_TABLE = os.getenv("PG_METRICS_TABLE", "stream_metrics_minute")
PG_STATE_TABLE = os.getenv("PG_STATE_TABLE", "stream_state")

# -----------------------------
# Event schema
# -----------------------------
EVENT_SCHEMA = StructType([
    StructField("event_id", StringType(), True),
    StructField("ts", StringType(), True),            # ISO timestamp string
    StructField("event_type", StringType(), True),    # viewer_join|viewer_leave|chat_message|donation
    StructField("stream_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("message_len", IntegerType(), True),
    StructField("amount_usd", DoubleType(), True),
])


def build_spark() -> SparkSession:
    spark = (
        SparkSession.builder
        .appName(APP_NAME)
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "4"))
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))
    return spark


def ensure_postgres_tables() -> None:
    """
    Create required tables if they don't exist.
    Runs inside the Spark container at startup (driver).
    """
    import psycopg2

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )
    conn.autocommit = True
    try:
        cur = conn.cursor()

        # State table: current active viewers per stream
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {PG_STATE_TABLE} (
          stream_id TEXT PRIMARY KEY,
          active_viewers INTEGER NOT NULL DEFAULT 0,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)

        # Metrics table: one row per window per stream
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {PG_METRICS_TABLE} (
          window_start TIMESTAMP NOT NULL,
          window_end   TIMESTAMP NOT NULL,
          stream_id    TEXT NOT NULL,
          active_viewers INTEGER NOT NULL,
          chat_messages BIGINT NOT NULL,
          donations_usd DOUBLE PRECISION NOT NULL,
          PRIMARY KEY (window_start, stream_id)
        );
        """)
    finally:
        conn.close()


def _get_active_viewers(cur, stream_id: str) -> int:
    cur.execute(
        f"SELECT active_viewers FROM {PG_STATE_TABLE} WHERE stream_id=%s",
        (stream_id,)
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _upsert_state(cur, stream_id: str, active: int) -> None:
    cur.execute(f"""
        INSERT INTO {PG_STATE_TABLE} (stream_id, active_viewers, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (stream_id) DO UPDATE
        SET active_viewers=EXCLUDED.active_viewers,
            updated_at=NOW();
    """, (stream_id, active))


def _upsert_metrics(cur, window_start, window_end, stream_id: str, active: int, chat_messages: int, donations_usd: float) -> None:
    cur.execute(f"""
        INSERT INTO {PG_METRICS_TABLE}
          (window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (window_start, stream_id) DO UPDATE
        SET window_end=EXCLUDED.window_end,
            active_viewers=EXCLUDED.active_viewers,
            chat_messages=EXCLUDED.chat_messages,
            donations_usd=EXCLUDED.donations_usd;
    """, (window_start, window_end, stream_id, active, chat_messages, donations_usd))


def upsert_batch_to_postgres(batch_df, batch_id: int) -> None:
    """
    foreachBatch sink: writes aggregated metrics + updates stream state (active viewers).
    batch_df columns:
      - window_start (timestamp)
      - window_end (timestamp)
      - stream_id (string)
      - delta_viewers (long/int)
      - chat_messages (long)
      - donations_usd (double)
    """
    # Avoid expensive work for empty micro-batches
    if batch_df.rdd.isEmpty():
        return

    # Collect should stay small: (#streams * #windows in this micro-batch)
    rows = (
        batch_df.select(
            "window_start", "window_end", "stream_id",
            "delta_viewers", "chat_messages", "donations_usd"
        )
        .orderBy("stream_id", "window_start")
        .collect()
    )

    if not rows:
        return

    import psycopg2

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )
    conn.autocommit = False

    try:
        cur = conn.cursor()

        current_stream: Optional[str] = None
        active = 0

        for r in rows:
            stream_id = r["stream_id"]

            # Load the current state once per stream per batch
            if current_stream != stream_id:
                current_stream = stream_id
                active = _get_active_viewers(cur, current_stream)

            delta = int(r["delta_viewers"]) if r["delta_viewers"] is not None else 0
            active = max(active + delta, 0)

            window_start = r["window_start"]
            window_end = r["window_end"]
            chat_messages = int(r["chat_messages"]) if r["chat_messages"] is not None else 0
            donations_usd = float(r["donations_usd"]) if r["donations_usd"] is not None else 0.0

            # metrics upsert (idempotent for update-mode)
            _upsert_metrics(cur, window_start, window_end, stream_id, active, chat_messages, donations_usd)

            # state upsert
            _upsert_state(cur, stream_id, active)

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"[foreachBatch] batch_id={batch_id} ERROR: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


def main() -> None:
    spark = build_spark()
    ensure_postgres_tables()

    # 1) Read from Kafka
    kafka_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", KAFKA_STARTING_OFFSETS)
        .option("failOnDataLoss", "false")
        .load()
    )

    # 2) Parse JSON
    parsed = (
        kafka_df.select(F.col("value").cast("string").alias("json_str"))
        .select(F.from_json(F.col("json_str"), EVENT_SCHEMA).alias("e"))
        .select("e.*")
    )

    # 3) Event time + watermark
    events = (
        parsed
        .withColumn("event_time", F.to_timestamp("ts"))
        .filter(F.col("event_time").isNotNull())
        .filter(F.col("stream_id").isNotNull())
        .withWatermark("event_time", WATERMARK_DELAY)
    )

    # 4) Windowed aggregation (minute)
    windowed = (
        events
        .groupBy(
            F.window(F.col("event_time"), WINDOW_DURATION).alias("window"),
            F.col("stream_id")
        )
        .agg(
            (
                F.count(F.when(F.col("event_type") == F.lit("viewer_join"), True)) -
                F.count(F.when(F.col("event_type") == F.lit("viewer_leave"), True))
            ).alias("delta_viewers"),
            F.count(F.when(F.col("event_type") == F.lit("chat_message"), True)).alias("chat_messages"),
            F.sum(
                F.when(F.col("event_type") == F.lit("donation"), F.col("amount_usd"))
                 .otherwise(F.lit(0.0))
            ).alias("donations_usd"),
        )
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.col("stream_id"),
            F.col("delta_viewers"),
            F.col("chat_messages"),
            F.col("donations_usd"),
        )
    )

    # 5) foreachBatch sink (Postgres holds the state)
    query = (
        windowed.writeStream
        # Update mode is fine because our sink is UPSERT + idempotent
        .outputMode("update")
        .trigger(processingTime=TRIGGER_INTERVAL)
        .option("checkpointLocation", CHECKPOINT_METRICS)
        .foreachBatch(upsert_batch_to_postgres)
        .queryName("stream_metrics_minute_to_postgres")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
