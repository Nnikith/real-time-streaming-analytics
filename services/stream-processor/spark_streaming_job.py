import os
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import execute_values

from pyspark.sql import SparkSession, functions as F, types as T


# -----------------------------
# Env / Config
# -----------------------------
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:29092")
TOPIC = os.getenv("KAFKA_TOPIC", os.getenv("TOPIC", "stream.events"))

CHECKPOINT = os.getenv(
    "CHECKPOINT",
    "/opt/spark-checkpoints/stream_metrics_minute_stateful"
)

WATERMARK = os.getenv("WATERMARK", "10 minutes")
WINDOW = os.getenv("WINDOW", "1 minute")

# Postgres config: prefer explicit vars, but accept PG_URL in JDBC form too
PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "realtime")
PG_USER = os.getenv("PG_USER", "rt")
PG_PASS = os.getenv("PG_PASS", "rt")

PG_URL = os.getenv("PG_URL", "")
# If someone provided jdbc url like: jdbc:postgresql://postgres:5432/realtime
# parse it and override host/port/db
if PG_URL.startswith("jdbc:postgresql://"):
    raw = PG_URL.replace("jdbc:", "", 1)
    u = urlparse(raw)
    if u.hostname:
        PG_HOST = u.hostname
    if u.port:
        PG_PORT = int(u.port)
    if u.path and len(u.path) > 1:
        PG_DB = u.path.lstrip("/")


METRICS_TABLE = os.getenv("PG_TABLE", "stream_metrics_minute")
STATE_TABLE = os.getenv("PG_STATE_TABLE", "stream_state")


# -----------------------------
# Helpers
# -----------------------------
def pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )


def ensure_tables():
    ddl_metrics = f"""
    CREATE TABLE IF NOT EXISTS {METRICS_TABLE} (
        window_start TIMESTAMPTZ NOT NULL,
        window_end   TIMESTAMPTZ NOT NULL,
        stream_id    TEXT        NOT NULL,
        active_viewers INTEGER   NOT NULL DEFAULT 0,
        chat_messages  INTEGER   NOT NULL DEFAULT 0,
        donations_usd  DOUBLE PRECISION NOT NULL DEFAULT 0,
        PRIMARY KEY (window_start, stream_id)
    );
    """

    ddl_state = f"""
    CREATE TABLE IF NOT EXISTS {STATE_TABLE} (
        stream_id TEXT PRIMARY KEY,
        active_viewers INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """

    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl_metrics)
            cur.execute(ddl_state)
        conn.commit()


def clamp_nonnegative(x: int) -> int:
    return 0 if x is None or x < 0 else x


# -----------------------------
# Spark Job
# -----------------------------
def main():
    spark = (
        SparkSession.builder
        .appName("realtime-streaming-analytics")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))

    ensure_tables()

    # Kafka JSON schema
    #
    # IMPORTANT FIX:
    # Your donation event uses: amount_usd
    # The previous code only had: amount
    # We support BOTH to be backward compatible.
    schema = T.StructType([
        T.StructField("event_id", T.StringType(), True),
        T.StructField("ts", T.StringType(), True),
        T.StructField("event_type", T.StringType(), True),
        T.StructField("stream_id", T.StringType(), True),
        T.StructField("user_id", T.StringType(), True),
        T.StructField("message_len", T.IntegerType(), True),
        T.StructField("amount_usd", T.DoubleType(), True),  # donation amount (correct field)
        T.StructField("amount", T.DoubleType(), True),      # legacy / fallback
    ])

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", os.getenv("STARTING_OFFSETS", "latest"))
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = (
        raw.selectExpr("CAST(value AS STRING) AS json_str")
        .select(F.from_json(F.col("json_str"), schema).alias("e"))
        .select("e.*")
    )

    # Parse ISO8601 timestamp with timezone + microseconds.
    # Example: 2025-12-20T18:34:38.300308+00:00
    # Also tolerate Z-suffix.
    parsed = (
        parsed
        .withColumn("ts_norm", F.regexp_replace(F.col("ts"), "Z$", "+00:00"))
        .withColumn(
            "event_ts",
            F.coalesce(
                F.to_timestamp("ts_norm", "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX"),
                F.to_timestamp("ts_norm", "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"),
                F.to_timestamp("ts_norm")
            )
        )
        .drop("ts_norm")
    )

    # Drop rows with no usable timestamp or stream_id
    events = (
        parsed
        .filter(F.col("event_ts").isNotNull())
        .filter(F.col("stream_id").isNotNull())
    )

    # Donation value: prefer amount_usd; fall back to amount
    events = events.withColumn(
        "donation_value_usd",
        F.coalesce(F.col("amount_usd"), F.col("amount"), F.lit(0.0)).cast("double")
    )

    # Derived metrics per event
    events = (
        events
        .withColumn(
            "chat_inc",
            F.when(F.col("event_type") == F.lit("chat_message"), F.lit(1)).otherwise(F.lit(0))
        )
        .withColumn(
            "don_usd",
            F.when(F.col("event_type") == F.lit("donation"), F.col("donation_value_usd")).otherwise(F.lit(0.0))
        )
        .withColumn(
            "viewer_delta",
            F.when(F.col("event_type") == F.lit("viewer_join"), F.lit(1))
             .when(F.col("event_type") == F.lit("viewer_leave"), F.lit(-1))
             .otherwise(F.lit(0))
        )
    )

    # Windowed aggregation
    windowed = (
        events
        .withWatermark("event_ts", WATERMARK)
        .groupBy(
            F.window(F.col("event_ts"), WINDOW).alias("w"),
            F.col("stream_id")
        )
        .agg(
            F.sum("chat_inc").cast("int").alias("chat_messages"),
            F.round(F.sum("don_usd"), 2).cast("double").alias("donations_usd"),
            F.sum("viewer_delta").cast("int").alias("net_viewer_delta")
        )
        .select(
            F.col("w.start").alias("window_start"),
            F.col("w.end").alias("window_end"),
            "stream_id",
            "chat_messages",
            "donations_usd",
            "net_viewer_delta",
        )
    )

    def write_batch(batch_df, batch_id: int):
        # Structured Streaming can call foreachBatch with empty DF
        if batch_df.rdd.isEmpty():
            return

        rows = batch_df.collect()

        # Build state updates and metrics upserts
        # Note: state update is "delta-based", metrics is "set semantics" per (window_start, stream_id)
        state_updates = []   # (stream_id, net_delta)
        metrics_rows = []    # (window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd)

        with pg_conn() as conn:
            with conn.cursor() as cur:
                # 1) Apply state deltas and fetch resulting active_viewers
                # We do this per stream_id (small cardinality) to keep logic correct.
                # (execute_values can't easily RETURNING per-row with ON CONFLICT updates.)
                active_map = {}

                for r in rows:
                    stream_id = r["stream_id"]
                    net_delta = int(r["net_viewer_delta"] or 0)
                    state_updates.append((stream_id, net_delta))

                # Deduplicate by stream_id for this batch (sum deltas within batch)
                delta_by_stream = {}
                for sid, d in state_updates:
                    delta_by_stream[sid] = delta_by_stream.get(sid, 0) + d

                for sid, dsum in delta_by_stream.items():
                    cur.execute(
                        f"""
                        INSERT INTO {STATE_TABLE} (stream_id, active_viewers, updated_at)
                        VALUES (%s, GREATEST(%s, 0), NOW())
                        ON CONFLICT (stream_id)
                        DO UPDATE SET
                          active_viewers = GREATEST({STATE_TABLE}.active_viewers + EXCLUDED.active_viewers, 0),
                          updated_at = NOW()
                        RETURNING active_viewers;
                        """,
                        (sid, dsum)
                    )
                    active_viewers = cur.fetchone()[0]
                    active_map[sid] = clamp_nonnegative(int(active_viewers or 0))

                # 2) Prepare metrics rows (overwrite semantics)
                for r in rows:
                    window_start = r["window_start"]
                    window_end = r["window_end"]
                    stream_id = r["stream_id"]
                    chat_messages = int(r["chat_messages"] or 0)
                    donations_usd = float(r["donations_usd"] or 0.0)
                    active_viewers = int(active_map.get(stream_id, 0))

                    metrics_rows.append(
                        (window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd)
                    )

                # Deduplicate metrics rows by (window_start, stream_id) keeping the last one
                # (Spark should already output one row per key, but this makes it bulletproof.)
                dedup = {}
                for tup in metrics_rows:
                    key = (tup[0], tup[2])  # (window_start, stream_id)
                    dedup[key] = tup
                metrics_rows = list(dedup.values())

                # Batch UPSERT metrics
                sql = f"""
                    INSERT INTO {METRICS_TABLE}
                      (window_start, window_end, stream_id, active_viewers, chat_messages, donations_usd)
                    VALUES %s
                    ON CONFLICT (window_start, stream_id)
                    DO UPDATE SET
                      window_end = EXCLUDED.window_end,
                      active_viewers = EXCLUDED.active_viewers,
                      chat_messages = EXCLUDED.chat_messages,
                      donations_usd = EXCLUDED.donations_usd;
                """
                execute_values(cur, sql, metrics_rows, page_size=1000)

            conn.commit()

    query = (
        windowed.writeStream
        .outputMode("update")
        .foreachBatch(write_batch)
        .option("checkpointLocation", CHECKPOINT)
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
