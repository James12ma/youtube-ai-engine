-- Alan7 bot state: jobs (queue), events (audit trail), meta (health markers).
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  arg TEXT,
  state TEXT NOT NULL,          -- queued | running | done | failed | cancelled | awaiting_approval
  attempts INTEGER NOT NULL DEFAULT 0,
  run_id INTEGER,
  last_error TEXT,
  next_try_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state, next_try_at);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT,
  event TEXT NOT NULL,
  detail TEXT,
  at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at INTEGER NOT NULL
);
