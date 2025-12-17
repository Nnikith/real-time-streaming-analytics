from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window, sum as Fsum, count as Fcount, when, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

KAFKA_BOOTSTRAP = "kafka:29092"
TOPIC = "stream.events"

PG_URL = "jdbc:postgresql://postgres:5432/realtime"
PG_USER = "rt"
PG_PASS = "rt"
PG_TABLE = "stream_metrics_minute"

schema = StructType([
    StructField("event_id", StringType()),
    StructField("ts", StringType()),
    StructField("event_type", StringType()),
    StructField("stream_id", StringType()),
    StructField("user_id", StringType()),
    StructField("message_len", IntegerType(), True),
    StructField("amount_usd", DoubleType(), True),
])

def main():
    spark = (SparkSession.builder
        .appName("realtime-stream-analytics")
        .getOrCreate())

    spark.sparkContext.setLogLevel("WARN")

    raw = (spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "latest")
        .load())

    parsed = (raw.selectExpr("CAST(value AS STRING) as json_str")
        .select(from_json(col("json_str"), schema).alias("e"))
        .select("e.*")
    )

    events = parsed.withColumn("event_time", to_timestamp(col("ts")))

    agg = (events
        .groupBy(window(col("event_time"), "1 minute"), col("stream_id"))
        .agg(
            Fcount(when(col("event_type") == "chat_message", True)).alias("chat_messages"),
            Fsum(when(col("event_type") == "donation", col("amount_usd")).otherwise(0.0)).alias("donations_usd"),
            (Fcount(when(col("event_type") == "viewer_join", True)) -
             Fcount(when(col("event_type") == "viewer_leave", True))).alias("active_viewers")
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("stream_id"),
            col("active_viewers"),
            col("chat_messages"),
            col("donations_usd")
        )
    )

    def write_to_postgres(batch_df, batch_id: int):
        (batch_df.write
            .format("jdbc")
            .option("url", PG_URL)
            .option("dbtable", PG_TABLE)
            .option("user", PG_USER)
            .option("password", PG_PASS)
            .mode("append")
            .save())

    query = (agg.writeStream
        .outputMode("update")
        .foreachBatch(write_to_postgres)
        .option("checkpointLocation", "/opt/spark-checkpoints/metrics_minute")
        .start())

    query.awaitTermination()

if __name__ == "__main__":
    main()
