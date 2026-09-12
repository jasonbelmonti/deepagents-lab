"""File-backed synthetic graph; short transactions, never a connection in PTC."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


class StaleRevision(ValueError):
    """The graph changed; explicitly refresh the investigation before continuing."""


class WorkBudgetExceeded(ValueError):
    """No complete answer was established within the work/transfer budget."""


@dataclass(frozen=True)
class Query:
    root: str = "p000000"
    topic: str = "graphs"
    since: str = "2025-01-01"
    max_hops: int = 3
    limit: int = 5

    def __post_init__(self):
        if not 1 <= self.max_hops <= 4 or not 1 <= self.limit <= 20:
            raise ValueError("Use 1–4 hops and 1–20 results.")


# Directed, simple paths. A result limit does not bound traversal work.
WALK = """
WITH RECURSIVE walk(id, path, hops) AS (
    SELECT id, id, 0 FROM people WHERE id = :root
    UNION ALL
    SELECT e.target, w.path || ',' || e.target, w.hops + 1
    FROM walk w JOIN edges e ON e.source = w.id
    WHERE w.hops < :max_hops AND e.kind = 'collaborated'
      AND e.last_seen >= :since
      AND instr(',' || w.path || ',', ',' || e.target || ',') = 0
)
"""


class GraphStore:
    """Each read checks a revision inside its own SQLite read transaction."""

    def __init__(self, path: Path, *, vm_budget: int = 2_000_000):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        if vm_budget < 100:
            raise ValueError("vm_budget must be at least 100.")
        self.vm_budget = vm_budget

    @contextmanager
    def read(self, revision: int | None = None) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        steps = 0

        def progress():
            nonlocal steps
            steps += 100
            return int(steps > self.vm_budget)

        db.set_progress_handler(progress, 100)
        try:
            db.execute("BEGIN")
            current = db.execute("SELECT revision FROM metadata").fetchone()[0]
            if revision is not None and current != revision:
                raise StaleRevision(f"Requested revision {revision}; current revision {current}. Refresh explicitly.")
            yield db
        except sqlite3.OperationalError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_INTERRUPT:
                raise WorkBudgetExceeded("SQLite VM work budget exceeded; result is incomplete.") from error
            raise
        finally:
            db.close()

    @property
    def revision(self) -> int:
        with self.read() as db:
            return db.execute("SELECT revision FROM metadata").fetchone()[0]

    def answer(self, query: Query, revision: int) -> list[dict]:
        with self.read(revision) as db:
            rows = db.execute(WALK + """
                , ranked AS (
                    SELECT id, path, hops,
                           row_number() OVER (PARTITION BY id ORDER BY hops, path) AS choice
                    FROM walk
                )
                SELECT r.id, r.path FROM ranked r JOIN people p ON p.id = r.id
                WHERE r.choice = 1 AND r.hops > 0 AND p.topic = :topic
                ORDER BY r.hops, r.id, r.path LIMIT :limit
            """, asdict(query)).fetchall()
            return [{"person_id": row["id"], "path": row["path"].split(",")} for row in rows]

    def materialize(self, query: Query, revision: int, *, bounded: bool, row_limit: int = 50_000) -> dict:
        with self.read(revision) as db:
            if bounded:
                ids = [row[0] for row in db.execute(
                    WALK + "SELECT DISTINCT id FROM walk LIMIT :cap",
                    {**asdict(query), "cap": row_limit + 1},
                )]
                if len(ids) > row_limit:
                    raise WorkBudgetExceeded("Subgraph node budget exceeded; result is incomplete.")
                if not ids:
                    return {"people": [], "edges": []}
                marks = ",".join("?" for _ in ids)
                people = db.execute(f"SELECT id, topic FROM people WHERE id IN ({marks}) ORDER BY id", ids).fetchall()
                edges = db.execute(f"""
                    SELECT source, target, kind, last_seen FROM edges
                    WHERE source IN ({marks}) AND target IN ({marks})
                      AND kind = 'collaborated' AND last_seen >= ? ORDER BY source, target
                    LIMIT ?
                """, [*ids, *ids, query.since, row_limit + 1]).fetchall()
            else:
                people = db.execute("SELECT * FROM people ORDER BY id LIMIT ?", (row_limit + 1,)).fetchall()
                edges = db.execute("SELECT * FROM edges ORDER BY source, target LIMIT ?", (row_limit + 1,)).fetchall()
            if max(len(people), len(edges)) > row_limit:
                raise WorkBudgetExceeded("Graph row budget exceeded; result is incomplete.")
            return {"people": [dict(row) for row in people], "edges": [dict(row) for row in edges]}

    def save_investigation(self, investigation_id: str, query: Query, revision: int) -> None:
        # A compact durable query record, not a graph snapshot or process-local handle.
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT revision FROM metadata").fetchone()[0] != revision:
                raise StaleRevision("Graph changed before saving the investigation.")
            db.execute("INSERT INTO investigations VALUES (?, ?, ?)",
                       (investigation_id, json.dumps(asdict(query), sort_keys=True), revision))

    def load_investigation(self, investigation_id: str) -> tuple[Query, int]:
        with self.read() as db:
            row = db.execute("SELECT query, revision FROM investigations WHERE id = ?", (investigation_id,)).fetchone()
            if row is None:
                raise KeyError(investigation_id)
            return Query(**json.loads(row["query"])), row["revision"]

    def remove_edge(self, source: str, target: str, *, expected_revision: int, operation_id: str) -> int:
        """Explicit host-side edit, with optimistic concurrency and retry protection."""
        request = json.dumps([source, target, expected_revision])
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT request, revision FROM operations WHERE id = ?", (operation_id,)).fetchone()
            if prior:
                if prior[0] != request:
                    raise ValueError("Operation ID reused for a different request.")
                return prior[1]
            current = db.execute("SELECT revision FROM metadata").fetchone()[0]
            if current != expected_revision:
                raise StaleRevision("Concurrent update; reload before editing.")
            cursor = db.execute("DELETE FROM edges WHERE source = ? AND target = ?", (source, target))
            if cursor.rowcount != 1:
                raise ValueError("Expected exactly one existing edge.")
            current += 1
            db.execute("UPDATE metadata SET revision = ?", (current,))
            db.execute("INSERT INTO operations VALUES (?, ?, ?)", (operation_id, request, current))
            return current
