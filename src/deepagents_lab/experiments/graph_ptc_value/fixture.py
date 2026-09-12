"""Small seeded social graphs, with opaque IDs and no answer-shaped endpoint."""
from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class GraphData:
    root: str
    profiles: dict[str, dict]
    edges: tuple[dict, ...]
    contacts: dict[str, str]


def make_graph(seed: int, width: int = 6) -> GraphData:
    rng = Random(seed)
    ids = [f"p-{value:08x}" for value in rng.sample(range(2**32), 4 * width + 1)]
    root, layers = ids[0], [ids[1 + i * width:1 + (i + 1) * width] for i in range(4)]
    profiles = {person: {"topic": rng.choice(("graphs", "security")), "name": f"Researcher {i}"}
                for i, person in enumerate(ids)}
    edges = {}

    def add(source, target, kind="collaborated", last_seen="2026-07-01"):
        edges[source, target, kind] = dict(source=source, target=target, kind=kind, last_seen=last_seen)

    for person in layers[0]:
        add(root, person)
    for first, second in zip(layers, layers[1:]):
        for index, person in enumerate(first):
            add(person, second[index])
            add(person, second[(index + 1) % width])
            add(person, rng.choice(second))
    # Old edges, unrelated edge kinds, a cycle and a reverse-only connection.
    add(root, layers[-1][0], "follows")
    add(root, layers[-1][1], last_seen="2025-01-01")
    add(layers[1][0], layers[0][0])
    add(layers[-1][-1], root)
    contacts = {person: ("2026-08-15" if i % 3 == 0 else "2025-01-01")
                for i, person in enumerate(ids) if i % 4 == 0}
    return GraphData(root, profiles, tuple(edges.values()), contacts)
