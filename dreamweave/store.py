"""SQLite-backed story storage. The browser cookie only holds an owner token."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field

SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    hero TEXT NOT NULL,
    world TEXT NOT NULL,
    parts TEXT NOT NULL,
    turns INTEGER NOT NULL DEFAULT 0,
    finished INTEGER NOT NULL DEFAULT 0,
    audio_file TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stories_owner_created ON stories (owner, created_at);
"""


@dataclass
class Story:
    id: str
    owner: str
    hero: str
    world: str
    parts: list[dict] = field(default_factory=list)  # {"kind": "story"|"choice", "text": str}
    turns: int = 0
    finished: bool = False
    audio_file: str | None = None
    created_at: float = 0.0

    @property
    def text(self) -> str:
        return "\n\n".join(p["text"] for p in self.parts if p["kind"] == "story")

    def public(self) -> dict:
        return {
            "id": self.id,
            "hero": self.hero,
            "world": self.world,
            "parts": self.parts,
            "turns": self.turns,
            "finished": self.finished,
            "has_audio": bool(self.audio_file),
        }


class StoryStore:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, owner: str, hero: str, world: str) -> Story:
        story = Story(id=uuid.uuid4().hex, owner=owner, hero=hero, world=world, created_at=time.time())
        self.save(story)
        return story

    def get(self, story_id: str) -> Story | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not row:
            return None
        return Story(
            id=row["id"], owner=row["owner"], hero=row["hero"], world=row["world"],
            parts=json.loads(row["parts"]), turns=row["turns"], finished=bool(row["finished"]),
            audio_file=row["audio_file"], created_at=row["created_at"],
        )

    def save(self, s: Story) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO stories (id, owner, hero, world, parts, turns, finished, audio_file, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET parts=excluded.parts, turns=excluded.turns,
                     finished=excluded.finished, audio_file=excluded.audio_file""",
                (s.id, s.owner, s.hero, s.world, json.dumps(s.parts), s.turns, int(s.finished), s.audio_file, s.created_at),
            )

    def count_recent(self, owner: str, seconds: float) -> int:
        with self._conn() as c:
            row = c.execute(
                "SELECT count(*) FROM stories WHERE owner = ? AND created_at > ?", (owner, time.time() - seconds)
            ).fetchone()
        return int(row[0])
