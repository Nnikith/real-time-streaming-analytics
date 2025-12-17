CREATE TABLE IF NOT EXISTS stream_metrics_minute (
  window_start TIMESTAMP NOT NULL,
  window_end   TIMESTAMP NOT NULL,
  stream_id    TEXT NOT NULL,
  active_viewers BIGINT NOT NULL,
  chat_messages  BIGINT NOT NULL,
  donations_usd  NUMERIC(12,2) NOT NULL,
  PRIMARY KEY (window_start, stream_id)
);
