"""Small, serialized SQLite writes; exports are never on the execution path."""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .security import redact


class Store:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "studio.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("PRAGMA user_version").fetchone()[0] > 1:
            self.db.close()
            raise ValueError("Database schema is newer than this application")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS objects(kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, status TEXT, created REAL, updated REAL, snapshot TEXT, prompt TEXT, error TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, kind TEXT, at REAL, body TEXT);
        CREATE INDEX IF NOT EXISTS events_run ON events(run_id,seq);
        CREATE TABLE IF NOT EXISTS messages(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, agent_id TEXT, body TEXT);
        CREATE INDEX IF NOT EXISTS messages_run ON messages(run_id,agent_id,seq);
        PRAGMA user_version=1;
        """)
        self.db.execute(
            "UPDATE runs SET status='interrupted', error='Application restarted during execution' WHERE status IN ('running','paused','waiting','queued')"
        )
        for row in self.db.execute(
            "SELECT id,body FROM objects WHERE kind='installation'"
        ).fetchall():
            body = json.loads(row["body"])
            if body.get("status") in ("running", "queued"):
                body.update(
                    status="interrupted",
                    error="Application restarted during installation",
                )
                self.put("installation", row["id"], body)
        self.db.commit()

    def put(self, kind: str, id: str, body: Any):
        if hasattr(body, "model_dump"):
            body = body.model_dump()
        body = redact(body)
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO objects VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
                (kind, id, json.dumps(body)),
            )
        return body

    def get(self, kind: str, id: str):
        with self.lock:
            row = self.db.execute(
                "SELECT body FROM objects WHERE kind=? AND id=?", (kind, id)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind: str):
        with self.lock:
            rows = self.db.execute(
                "SELECT body FROM objects WHERE kind=? ORDER BY rowid", (kind,)
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete(self, kind: str, id: str):
        with self.lock, self.db:
            self.db.execute("DELETE FROM objects WHERE kind=? AND id=?", (kind, id))

    def create_run(self, id: str, snapshot: dict, prompt: str):
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO runs(id,status,created,updated,snapshot,prompt) VALUES(?,?,?,?,?,?)",
                (id, "queued", time.time(), time.time(), json.dumps(snapshot), prompt),
            )

    def update_run(self, id: str, status: str, error: str = ""):
        with self.lock, self.db:
            self.db.execute(
                "UPDATE runs SET status=?,updated=?,error=? WHERE id=?",
                (status, time.time(), error, id),
            )

    def run(self, id: str):
        with self.lock:
            row = self.db.execute("SELECT * FROM runs WHERE id=?", (id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["snapshot"] = json.loads(result["snapshot"])
        return result

    def runs(self):
        with self.lock:
            return [
                dict(r)
                for r in self.db.execute(
                    "SELECT id,status,created,updated,error,prompt FROM runs ORDER BY created DESC"
                ).fetchall()
            ]

    def event(self, run_id: str, kind: str, body: dict):
        with self.lock, self.db:
            cursor = self.db.execute(
                "INSERT INTO events(run_id,kind,at,body) VALUES(?,?,?,?)",
                (run_id, kind, time.time(), json.dumps(redact(body), default=str)),
            )
            return cursor.lastrowid

    def events(self, run_id: str, after: int = 0):
        with self.lock:
            rows = self.db.execute(
                "SELECT * FROM events WHERE run_id=? AND seq>? ORDER BY seq LIMIT 1000",
                (run_id, after),
            ).fetchall()
        return [{**dict(r), "body": json.loads(r["body"])} for r in rows]

    def latest_network(self, run_id: str):
        with self.lock:
            row = self.db.execute(
                "SELECT body FROM events WHERE run_id=? AND kind IN ('summary','network_changed','run_snapshot') ORDER BY seq DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        return json.loads(row[0])["network"] if row else None

    def message(self, run_id: str, agent_id: str, body: dict):
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO messages(run_id,agent_id,body) VALUES(?,?,?)",
                (run_id, agent_id, json.dumps(redact(body))),
            )

    def messages(self, run_id: str, agent_id: str | None = None):
        query, args = "SELECT * FROM messages WHERE run_id=?", [run_id]
        if agent_id is not None:
            query += " AND agent_id=?"
            args.append(agent_id)
        with self.lock:
            rows = self.db.execute(query + " ORDER BY seq", args).fetchall()
        return [
            {"seq": r["seq"], "agent_id": r["agent_id"], **json.loads(r["body"])}
            for r in rows
        ]

    def close(self):
        self.db.close()
