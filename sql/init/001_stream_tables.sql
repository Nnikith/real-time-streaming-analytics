-- sql/init/001_stream_tables.sql
-- Creates the tables needed by the streaming pipeline.

CREATE TABLE IF NOT EXISTS stream_metrics_minute (
  window_start    TIMESTAMPTZ NOT NULL,
  window_end      TIMESTAMPTZ NOT NULL,
  stream_id       TEXT        NOT NULL,
  active_viewers  INTEGER     NOT NULL DEFAULT 0,
  chat_messages   INTEGER     NOT NULL DEFAULT 0,
  donations_usd   DOUBLE PRECISION NOT NULL DEFAULT 0,
  PRIMARY KEY (window_start, stream_id)
);

CREATE TABLE IF NOT EXISTS stream_state (
  stream_id       TEXT PRIMARY KEY,
  active_viewers  INTEGER     NOT NULL DEFAULT 0,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Helpful indexes (optional but good)
CREATE INDEX IF NOT EXISTS idx_stream_metrics_minute_stream
  ON stream_metrics_minute (stream_id);

CREATE INDEX IF NOT EXISTS idx_stream_metrics_minute_window
  ON stream_metrics_minute (window_start DESC);
