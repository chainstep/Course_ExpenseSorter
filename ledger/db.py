"""SQLite schema and connection helpers."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ledger.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  merchant TEXT NOT NULL,
  amount REAL NOT NULL,
  category TEXT,
  category_source TEXT,
  import_file TEXT,
  hash TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS tx_embeddings (
  tx_id INTEGER PRIMARY KEY REFERENCES transactions(id),
  vector BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS token_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  month TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_tokens INTEGER NOT NULL,
  eval_tokens INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
  month TEXT PRIMARY KEY,
  token_budget INTEGER NOT NULL
);
"""


def _connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Path | None = None) -> None:
    """Create tables if they don't exist (idempotent)."""
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def db_path() -> Path:
    return DB_PATH


__all__ = ["connect", "init_db", "db_path", "SCHEMA", "DATA_DIR"]