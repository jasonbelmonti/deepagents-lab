"""Bounded experiment inputs; no service or default-agent configuration."""
from dataclasses import dataclass
from math import isfinite

from deepagents_lab.agent import DEFAULT_MODEL

ARMS = ("ordinary", "compute", "ptc")


@dataclass(frozen=True)
class Scenario:
    name: str = "depth-3"
    kind: str = "introductions"
    depth: int = 3
    width: int = 6
    topic: str = "graphs"
    min_connectors: int = 1
    limit: int = 5
    edge_since: str = "2026-01-01"
    contact_since: str = "2026-08-01"

    def __post_init__(self):
        from datetime import date
        from re import fullmatch

        if not fullmatch(r"[a-z][a-z0-9-]{0,63}", self.name) or self.kind not in ("lookup", "introductions"):
            raise ValueError("Name a lookup or introductions scenario.")
        if any(type(value) is not int for value in (self.depth, self.width, self.min_connectors, self.limit)):
            raise ValueError("Depth, width, connector count and limit must be integers.")
        if not 2 <= self.depth <= 4 or not 3 <= self.width <= 12:
            raise ValueError("Use depth 2–4 and width 3–12.")
        if not 1 <= self.limit <= 10 or not 1 <= self.min_connectors <= self.width:
            raise ValueError("Use limit 1–10 and a feasible minimum connector count.")
        for value in (self.edge_since, self.contact_since):
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("Dates must use YYYY-MM-DD.")


CASES = (
    Scenario(name="lookup", kind="lookup"),
    Scenario(name="depth-2", depth=2),
    Scenario(),
    Scenario(name="width-12", width=12),
)
# Query variation on unchanged graph APIs. Not included in the default pilot.
VARIANT = Scenario(name="security-two-connectors", topic="security", min_connectors=2)


@dataclass(frozen=True)
class Config:
    model: str = DEFAULT_MODEL
    seeds: tuple[int, ...] = (1103, 2213)
    cases: tuple[Scenario, ...] = CASES
    run_timeout: float = 180
    model_timeout: float = 60
    interpreter_timeout: float = 10
    max_tool_calls: int = 64
    concurrency: int = 4
    recursion_limit: int = 48

    def __post_init__(self):
        if not self.model or not 1 <= len(self.seeds) <= 20 or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Specify a model and 1–20 distinct seeds.")
        if any(type(seed) is not int or not 0 <= seed < 2**32 for seed in self.seeds):
            raise ValueError("Seeds must be unsigned 32-bit integers.")
        if not 1 <= len(self.cases) <= 8 or len({c.name for c in self.cases}) != len(self.cases):
            raise ValueError("Specify 1–8 uniquely named scenarios.")
        if any(not isfinite(t) or t <= 0 for t in (self.run_timeout, self.model_timeout, self.interpreter_timeout)):
            raise ValueError("Timeouts must be positive and finite.")
        if any(type(value) is not int for value in (self.max_tool_calls, self.concurrency, self.recursion_limit)):
            raise ValueError("Call, concurrency and recursion limits must be integers.")
        if not 8 <= self.max_tool_calls <= 256 or not 1 <= self.concurrency <= 8 or not 12 <= self.recursion_limit <= 100:
            raise ValueError("Use 8–256 tool calls, concurrency 1–8 and recursion limit 12–100.")

    @property
    def planned_runs(self):
        return len(self.seeds) * len(self.cases) * len(ARMS)


def arm_order(index: int) -> tuple[str, ...]:
    """Reverse adjacent blocks; cover all six permutations across six seeds."""
    rotation = (index // 2) % len(ARMS)
    order = ARMS[rotation:] + ARMS[:rotation]
    return order if index % 2 == 0 else order[::-1]
