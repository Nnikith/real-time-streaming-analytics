-- adapt if your table already exists
CREATE TABLE IF NOT EXISTS stream_metrics_minute (
  window_start TIMESTAMP NOT NULL,
  window_end   TIMESTAMP NOT NULL,
  stream_id    TEXT NOT NULL,
  active_viewers INTEGER NOT NULL,
  chat_messages BIGINT NOT NULL,
  donations_usd DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (window_start, stream_id)
);

CREATE TABLE IF NOT EXISTS stream_state (
  stream_id TEXT PRIMARY KEY,
  active_viewers INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
