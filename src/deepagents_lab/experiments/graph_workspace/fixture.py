"""Deterministic disconnected communities, plus optional high-degree root."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .store import GraphStore


def create_fixture(path: Path, *, people: int = 1000, payload_bytes: int = 256, hub_edges: int = 0) -> GraphStore:
    """Create a fresh database only; never overwrite an existing experiment."""
    if not 31 <= people <= 100_000 or not 0 <= payload_bytes <= 2048:
        raise ValueError("Use 31–100,000 people and 0–2,048 payload bytes.")
    if not 0 <= hub_edges <= people // 31 - 1:
        raise ValueError("hub_edges must fit the other communities.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb"):
        pass
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE people(id TEXT PRIMARY KEY, topic TEXT NOT NULL, profile TEXT NOT NULL);
            CREATE TABLE edges(source TEXT, target TEXT, kind TEXT, last_seen TEXT,
                               PRIMARY KEY(source, target));
            CREATE INDEX edges_lookup ON edges(source, kind, last_seen, target);
            CREATE TABLE metadata(revision INTEGER NOT NULL);
            INSERT INTO metadata VALUES (1);
            CREATE TABLE investigations(id TEXT PRIMARY KEY, query TEXT NOT NULL, revision INTEGER NOT NULL);
            CREATE TABLE operations(id TEXT PRIMARY KEY, request TEXT NOT NULL, revision INTEGER NOT NULL);
        """)
        db.executemany("INSERT INTO people VALUES (?, ?, ?)", (
            (f"p{i:06}", "graphs" if i % 3 == 0 else "other", "x" * payload_bytes)
            for i in range(people)
        ))
        edges = []
        for i in range(people):
            base, local = i // 31 * 31, i % 31
            for child in (2 * local + 1, 2 * local + 2):
                if child < 31 and base + child < people:
                    edges.append((f"p{i:06}", f"p{base + child:06}", "collaborated", "2026-01-01"))
            if local == 0 and i + 31 < people:
                edges.append((f"p{i:06}", f"p{i + 31:06}", "follows", "2026-01-01"))
        # A recent collaboration is intentionally distinct from a follows edge.
        indexed = {edge[:2]: edge for edge in edges}
        for community in range(1, hub_edges + 1):
            target = f"p{community * 31:06}"
            indexed[("p000000", target)] = ("p000000", target, "collaborated", "2026-01-01")
        db.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)", indexed.values())
    return GraphStore(path)
