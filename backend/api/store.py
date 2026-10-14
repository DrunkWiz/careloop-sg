"""Storage. One table of JSON documents keyed by (kind, id), indexed by senior and day.

Hosting decision (Tue): the two apps run on two phones and must share state, so the API runs
as ONE always-on service against ONE database, never per-instance SQLite on serverless.
  - DATABASE_URL=postgresql://...  -> Postgres (deploy: managed Postgres, e.g. TencentDB or Neon)
  - otherwise CARELOOP_DB=path     -> SQLite file (local dev, the demo laptop, tests use :memory:)
Same SQL for both; only the placeholder style differs.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Iterable

KINDS = ("senior", "contact", "reading", "checkin", "envday", "decision", "message", "handover",
         "suggestion", "knows", "paircode", "programme", "carenotes")  # carenotes: added by Nathan, needs team OK

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  kind TEXT NOT NULL,
  id TEXT NOT NULL,
  senior_id TEXT,
  day TEXT,
  body TEXT NOT NULL,
  PRIMARY KEY (kind, id)
);
CREATE INDEX IF NOT EXISTS docs_senior_day ON docs (kind, senior_id, day);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class Store:
    def __init__(self, url: str | None = None):
        url = url if url is not None else os.environ.get("DATABASE_URL") or os.environ.get("CARELOOP_DB", "careloop.db")
        self.pg = url.startswith(("postgres://", "postgresql://"))
        self._lock = threading.RLock()
        if self.pg:
            import psycopg  # only needed when deployed against Postgres

            self.conn = psycopg.connect(url, autocommit=True)
            self.ph = "%s"
        else:
            self.conn = sqlite3.connect(url, check_same_thread=False, isolation_level=None)
            self.conn.execute("PRAGMA journal_mode=WAL") if url != ":memory:" else None
            self.ph = "?"
        for stmt in SCHEMA.strip().split(";"):
            if stmt.strip():
                self.conn.execute(stmt)

    def _q(self, sql: str) -> str:
        return sql.replace("?", self.ph)

    def _exec(self, sql: str, args: Iterable = ()):
        with self._lock:
            return self.conn.execute(self._q(sql), tuple(args))

    # documents
    def put(self, kind: str, doc: dict, *, day: str | None = None) -> dict:
        assert kind in KINDS, kind
        day = day or doc.get("date") or (doc.get("time") or "")[:10] or None
        upsert = ("INSERT INTO docs (kind, id, senior_id, day, body) VALUES (?, ?, ?, ?, ?) "
                  "ON CONFLICT (kind, id) DO UPDATE SET senior_id = excluded.senior_id, day = excluded.day, body = excluded.body")
        self._exec(upsert, (kind, doc["id"], doc.get("senior_id"), day, json.dumps(doc, ensure_ascii=False)))
        return doc

    def get(self, kind: str, id: str) -> dict | None:
        row = self._exec("SELECT body FROM docs WHERE kind = ? AND id = ?", (kind, id)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind: str, *, senior_id: str | None = None, day_from: str | None = None,
             day_to: str | None = None) -> list[dict]:
        sql, args = "SELECT body FROM docs WHERE kind = ?", [kind]
        if senior_id is not None:
            sql += " AND senior_id = ?"
            args.append(senior_id)
        if day_from is not None:
            sql += " AND day >= ?"
            args.append(day_from)
        if day_to is not None:
            sql += " AND day <= ?"
            args.append(day_to)
        sql += " ORDER BY day, id"
        return [json.loads(r[0]) for r in self._exec(sql, args).fetchall()]

    def delete(self, kind: str, id: str) -> bool:
        return self._exec("DELETE FROM docs WHERE kind = ? AND id = ?", (kind, id)).rowcount > 0

    # settings (the demo clock lives here)
    def setting(self, key: str, default: str | None = None) -> str | None:
        row = self._exec("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._exec("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value", (key, value))

    def clear(self) -> None:
        self._exec("DELETE FROM docs")
        self._exec("DELETE FROM settings")
