"""A small, inspectable network with deliberately misleading alternatives."""

from dataclasses import astuple
from pathlib import Path

import duckdb

from .domain import Employment, Network, Relationship


def make_network(hub_size: int = 30) -> Network:
    if not 1 <= hub_size <= 1000:
        raise ValueError("hub_size must be between 1 and 1000")
    people = [
        ("user", "You"), ("vera", "Vera Chen"), ("maya", "Maya Patel"),
        ("chris", "Chris Morgan"), ("ari", "Ari Jones"), ("sam", "Sam Rivera"),
        ("leo", "Leo Park"), ("nina", "Nina Shah"), ("hub", "A well-connected contact"),
        ("former", "Former employee"), ("wrong-team", "Employee on another team"),
        ("stale", "Long-ago collaborator"), ("reverse", "Reverse-only contact"),
        ("affiliation", "Shared-school contact"), ("future", "Future-dated contact"),
        ("not-started", "Future employee"),
    ]
    edges = []

    def edge(source, target, strength=5, observed="2026-08-01", kind="collaborated"):
        edges.append(Relationship(
            source, target, kind, strength, observed, f"rel-{source}-{target}",
            f"Synthetic {kind} evidence: {source} can approach {target}.",
        ))

    edge("user", "vera", observed="2026-08-25")  # Direct target-team employee.
    edge("user", "maya")
    edge("maya", "leo", observed="2026-09-01")
    edge("maya", "nina", observed="2026-09-01")  # Same connector, tied strength/date.
    edge("maya", "user")  # Cycle; never a new independent connector.
    edge("user", "chris", 4, "2026-09-01")
    edge("chris", "nina", 4, "2026-08-20", "mentor")
    edge("user", "ari", 4, "2026-09-03")
    edge("ari", "sam", 4, "2026-09-02")
    edge("sam", "leo", 4, "2026-09-02")
    edge("user", "hub", 1, "2026-09-09")  # Fanout cannot repair this weak first edge.
    edge("user", "former")
    edge("user", "wrong-team")
    edge("user", "not-started")
    edge("user", "stale", observed="2024-01-01")
    edge("stale", "leo")
    edge("reverse", "user")  # Direction cannot be inferred or reversed.
    edge("reverse", "leo")
    edge("user", "affiliation", kind="shared_school")
    edge("affiliation", "leo")
    edge("user", "future", observed="2026-09-14")
    edge("future", "leo")
    employment = [
        Employment(p, "atlas", "Infrastructure", "2025-01-01", None, f"emp-{p}")
        for p in ("vera", "leo", "nina")
    ]
    employment.extend([
        Employment("former", "atlas", "Infrastructure", "2024-01-01", "2026-09-01", "emp-former"),
        Employment("wrong-team", "atlas", "Sales", "2025-01-01", None, "emp-wrong-team"),
        Employment("not-started", "atlas", "Infrastructure", "2026-10-01", None, "emp-not-started"),
    ])
    for index in range(hub_size):
        person = f"hub-employee-{index:04d}"
        people.append((person, f"Hub colleague {index}"))
        edge("hub", person, observed="2026-09-09")
        employment.append(Employment(person, "atlas", "Infrastructure", "2025-01-01", None, f"emp-{person}"))
    return Network(tuple(people), tuple(edges), tuple(employment), (
        ("job-infra", "atlas", "Infrastructure", "Senior Infrastructure Engineer"),
    ))


def create_fixture(path: Path, network: Network) -> Path:
    """Create a fresh file; leave all writes on the host outside the agent."""
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as connection:
        connection.execute("""
            CREATE TABLE people (person_id VARCHAR PRIMARY KEY, name VARCHAR);
            CREATE TABLE relationships (
                source_id VARCHAR, target_id VARCHAR, kind VARCHAR,
                strength INTEGER CHECK (strength BETWEEN 1 AND 5), observed_at DATE,
                evidence_id VARCHAR PRIMARY KEY, evidence_note VARCHAR,
                UNIQUE (source_id, target_id)
            );
            CREATE TABLE employment (
                person_id VARCHAR, company_id VARCHAR, team VARCHAR,
                starts_at DATE, ends_at DATE, evidence_id VARCHAR PRIMARY KEY
            );
            CREATE TABLE jobs (job_id VARCHAR PRIMARY KEY, company_id VARCHAR, team VARCHAR, title VARCHAR);
        """)
        for table, rows, count in (
            ("people", network.people, 2),
            ("relationships", [astuple(edge) for edge in network.relationships], 7),
            ("employment", [astuple(job) for job in network.employment], 6),
            ("jobs", network.jobs, 4),
        ):
            if rows:
                connection.executemany(f"INSERT INTO {table} VALUES ({','.join(['?'] * count)})", rows)
    return path.resolve()
