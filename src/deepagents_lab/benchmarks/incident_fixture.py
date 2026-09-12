"""Deterministic four-stage incident API with auditable record coverage."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from threading import Lock
from time import perf_counter
from typing import Any

from langchain_core.tools import tool

STAGES = ("fetch_incidents", "fetch_evidence", "fetch_service_context", "classify_incidents")


class IncidentFixture:
    """A fresh instance belongs to one trial; both arms use identical data."""

    def __init__(self, records: int = 20, payload_bytes: int = 1536) -> None:
        if not 1 <= records <= 20 or not 1024 <= payload_bytes <= 2048:
            raise ValueError("Use 1–20 records and 1024–2048 bytes per intermediate record.")
        self.ids = [f"INC-{index:03}" for index in range(1, records + 1)]
        self.payload_bytes = payload_bytes
        self.calls: list[dict[str, Any]] = []
        self._lock = Lock()
        self._completed = [set() for _ in STAGES]
        self._references = [
            {
                incident: hashlib.sha256(f"triage-v1:{stage}:{incident}".encode()).hexdigest()[:12]
                for incident in self.ids
            }
            for stage in range(3)
        ]
        self.decisions = [
            {
                "incident_id": incident,
                "priority": "P1" if index % 5 == 0 else "P2" if index % 3 == 0 else "P3",
                "owner": ("payments", "platform", "identity")[index % 3],
            }
            for index, incident in enumerate(self.ids, start=1)
        ]

    @property
    def expected(self) -> list[dict[str, str]]:
        return sorted(
            [row for row in self.decisions if row["priority"] != "P3"],
            key=lambda row: (row["priority"], row["incident_id"]),
        )

    def _record(self, stage: int, incident: str) -> dict[str, Any]:
        if stage == 3:
            return dict(self.decisions[self.ids.index(incident)])
        reference_key = ("evidence_ref", "context_ref", "decision_ref")[stage]
        row = {
            "incident_id": incident,
            reference_key: self._references[stage][incident],
            "diagnostic_history": "",
        }
        # ASCII JSON has one byte per character. These controlled synthetic logs
        # emulate API history fields that are irrelevant to the next lookup.
        available = self.payload_bytes - len(json.dumps(row).encode())
        history = "\n".join(
            f"{incident} stage={stage} sample={sample}: request latency elevated; "
            "replica health checked; deployment correlation pending; retain for audit."
            for sample in range(30)
        ).replace("\n", " ")
        row["diagnostic_history"] = history[:available]
        return row

    def execute(self, stage: int, references: list[str]) -> list[dict[str, Any]]:
        """Validate actual dependencies and retain failed as well as successful calls."""
        started = perf_counter()
        with self._lock:
            entry: dict[str, Any] = {"stage": STAGES[stage], "ids": [], "ok": False}
            try:
                if not references or len(set(references)) != len(references):
                    raise ValueError("Supply a nonempty batch without duplicate references.")
                lookup = (
                    {incident: incident for incident in self.ids}
                    if stage == 0
                    else {ref: incident for incident, ref in self._references[stage - 1].items()}
                )
                ids = [lookup[reference] for reference in references]
                entry["ids"] = ids
                if stage and not set(ids) <= self._completed[stage - 1]:
                    raise ValueError("Retrieve the preceding stage before following its references.")
                output = [self._record(stage, incident) for incident in ids]
                self._completed[stage].update(ids)
                entry["ok"] = True
                return output
            except KeyError as error:
                raise ValueError("Unknown reference; use the preceding tool's returned reference.") from error
            finally:
                entry["elapsed_seconds"] = perf_counter() - started
                self.calls.append(entry)

    def coverage_ok(self) -> bool:
        """Every record must have succeeded exactly once in every stage."""
        return all(call["ok"] for call in self.calls) and all(
            Counter(
                incident
                for call in self.calls
                if call["stage"] == stage
                for incident in call["ids"]
            ) == Counter(self.ids)
            for stage in STAGES
        )

    def tools(self) -> list[Any]:
        @tool
        def fetch_incidents(incident_ids: list[str]) -> list[dict[str, Any]]:
            """Batch-load incidents. Returns evidence_ref per record; pass these to fetch_evidence."""
            return self.execute(0, incident_ids)

        @tool
        def fetch_evidence(evidence_refs: list[str]) -> list[dict[str, Any]]:
            """Batch-load evidence using evidence_ref from fetch_incidents; returns context_ref."""
            return self.execute(1, evidence_refs)

        @tool
        def fetch_service_context(context_refs: list[str]) -> list[dict[str, Any]]:
            """Batch-load service context using context_ref from fetch_evidence; returns decision_ref."""
            return self.execute(2, context_refs)

        @tool
        def classify_incidents(decision_refs: list[str]) -> list[dict[str, Any]]:
            """Batch-classify using decision_ref from fetch_service_context; returns priority and owner."""
            return self.execute(3, decision_refs)

        return [fetch_incidents, fetch_evidence, fetch_service_context, classify_incidents]
