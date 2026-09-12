"""Independent full-fixture path enumeration, never exposed to agent tools."""
from collections import defaultdict

from .config import Scenario
from .fixture import GraphData


def structural_candidates(data: GraphData, case: Scenario) -> list[dict]:
    """Rank all structurally eligible candidates before profile/contact filtering."""
    adjacency = defaultdict(set)
    for edge in data.edges:
        if edge["kind"] == "collaborated" and edge["last_seen"] >= case.edge_since:
            adjacency[edge["source"]].add(edge["target"])
    paths = defaultdict(lambda: defaultdict(list))

    def visit(path):
        person = path[-1]
        if len(path) >= 3 and person not in adjacency[data.root]:
            paths[person][path[1]].append(path)
        if len(path) <= case.depth:
            for target in sorted(adjacency[person]):
                if target not in path:
                    visit([*path, target])

    visit([data.root])
    answers = []
    for person, by_connector in paths.items():
        if len(by_connector) < case.min_connectors:
            continue
        representatives = [min(by_connector[c], key=lambda p: (len(p), p)) for c in sorted(by_connector)]
        answers.append({"person_id": person, "connectors": len(by_connector), "paths": representatives})
    answers.sort(key=lambda row: (-row["connectors"], min(map(len, row["paths"])), row["person_id"]))
    return answers


def expected_answer(data: GraphData, case: Scenario) -> list[dict]:
    if case.kind == "lookup":
        return [{"person_id": data.root, "topic": data.profiles[data.root]["topic"]}]
    return [row for row in structural_candidates(data, case)
            if data.profiles[row["person_id"]]["topic"] == case.topic
            and data.contacts.get(row["person_id"], "") < case.contact_since][:case.limit]
