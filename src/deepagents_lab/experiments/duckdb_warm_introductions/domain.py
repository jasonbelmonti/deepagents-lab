"""Fixture records and the explicit, non-probabilistic ranking rules."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Relationship:
    source_id: str
    target_id: str
    kind: str
    strength: int
    observed_at: str
    evidence_id: str
    evidence_note: str


@dataclass(frozen=True)
class Employment:
    person_id: str
    company_id: str
    team: str
    starts_at: str
    ends_at: str | None
    evidence_id: str


@dataclass(frozen=True)
class Network:
    people: tuple[tuple[str, str], ...]
    relationships: tuple[Relationship, ...]
    employment: tuple[Employment, ...]
    jobs: tuple[tuple[str, str, str, str], ...]


@dataclass(frozen=True)
class Question:
    user_id: str = "user"
    job_id: str = "job-infra"
    as_of: str = "2026-09-13"
    cutoff: str = "2025-09-13"
    max_hops: int = 3
    top_k: int = 4

    def __post_init__(self):
        if date.fromisoformat(self.cutoff) > date.fromisoformat(self.as_of):
            raise ValueError("cutoff must be on or before as_of")
        if not 1 <= self.max_hops <= 3 or not 1 <= self.top_k <= 10:
            raise ValueError("Use 1–3 hops and 1–10 connectors for this bounded experiment")
