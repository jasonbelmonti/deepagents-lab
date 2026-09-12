"""Read-only PTC boundary with per-run transfer/work telemetry."""
from __future__ import annotations

import json
from dataclasses import asdict
from threading import Lock
from time import perf_counter

from langchain_core.tools import tool

from .store import GraphStore, Query, WorkBudgetExceeded

ARMS = ("eager", "bounded", "backend")


class GraphTools:
    def __init__(self, store: GraphStore, query: Query, revision: int, arm: str, *, byte_budget: int = 8_000_000):
        if arm not in ARMS or byte_budget < 1:
            raise ValueError("Choose eager/bounded/backend and a positive byte budget.")
        self.store, self.query, self.revision, self.arm = store, query, revision, arm
        self.byte_budget = byte_budget
        self.calls: list[dict] = []
        self._lock = Lock()

    def tools(self):
        @tool
        def read_graph() -> dict:
            """Read this investigation's fixed graph view. Eager/bounded return people and edges;
            backend returns exact ranked answers. All return query and revision. No writes."""
            started = perf_counter()
            row = {"ok": False, "response_bytes": 0}
            try:
                if self.arm == "backend":
                    payload = {"answers": self.store.answer(self.query, self.revision)}
                else:
                    payload = self.store.materialize(self.query, self.revision, bounded=self.arm == "bounded")
                payload.update(query=asdict(self.query), revision=self.revision)
                row["response_bytes"] = len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
                row["people_returned"] = len(payload.get("people", []))
                row["edges_returned"] = len(payload.get("edges", []))
                row["answers_returned"] = len(payload.get("answers", []))
                if row["response_bytes"] > self.byte_budget:
                    raise WorkBudgetExceeded("PTC transfer budget exceeded; no complete result.")
                row["ok"] = True
                return payload
            except Exception as error:
                row["error_type"] = type(error).__name__
                raise
            finally:
                row["backend_ms"] = (perf_counter() - started) * 1000
                with self._lock:
                    self.calls.append(row)

        return [read_graph]
