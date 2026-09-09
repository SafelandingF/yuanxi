import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .seed import seed_candidates


class Store:
    def __init__(self, path: Path):
        candidates = seed_candidates()  # Validate before making any database changes.
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            # Append-only import: retain existing candidates and all private sessions.
            # A fresh clone imports the full catalog; an older database gets new IDs.
            db.executemany(
                "INSERT INTO candidates VALUES (?,?) ON CONFLICT(id) DO NOTHING",
                [(c["id"], json.dumps(c, ensure_ascii=False)) for c in candidates],
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def candidates(self):
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute("SELECT data FROM candidates ORDER BY id")
            ]

    def save(self, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?,?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT data FROM sessions WHERE id=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None
