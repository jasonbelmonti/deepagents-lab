from dataclasses import replace

import pytest

from deepagents_lab.experiments.graph_ptc_value.config import CASES, Config, Scenario, arm_order
from deepagents_lab.experiments.graph_ptc_value.coverage import sufficient_reads
from deepagents_lab.experiments.graph_ptc_value.fixture import GraphData, make_graph
from deepagents_lab.experiments.graph_ptc_value.oracle import expected_answer
from deepagents_lab.experiments.graph_ptc_value.tools import GraphAPI


def known_graph():
    profiles = {p: {"topic": "graphs", "name": p} for p in "rabcxyz"}
    edges = tuple(dict(source=a, target=b, kind=kind, last_seen=date) for a, b, kind, date in (
        ("r", "a", "collaborated", "2026-07-01"), ("r", "b", "collaborated", "2026-07-01"),
        ("a", "x", "collaborated", "2026-07-01"), ("b", "x", "collaborated", "2026-07-01"),
        ("a", "c", "collaborated", "2026-07-01"), ("c", "x", "collaborated", "2026-07-01"),
        ("c", "y", "collaborated", "2026-07-01"), ("x", "a", "collaborated", "2026-07-01"),
        ("b", "z", "collaborated", "2025-01-01"), ("a", "z", "follows", "2026-07-01"),
        ("z", "r", "collaborated", "2026-07-01"),
    ))
    return GraphData("r", profiles, edges, {"c": "2026-08-01"})


def test_known_paths_contact_cutoff_ranking_and_directions():
    graph = known_graph()
    assert expected_answer(graph, Scenario()) == [
        {"person_id": "x", "connectors": 2, "paths": [["r", "a", "x"], ["r", "b", "x"]]},
        {"person_id": "y", "connectors": 1, "paths": [["r", "a", "c", "y"]]},
    ]
    assert expected_answer(graph, Scenario(depth=2)) == expected_answer(graph, Scenario())[:1]
    assert expected_answer(graph, Scenario(min_connectors=2)) == expected_answer(graph, Scenario())[:1]
    assert expected_answer(graph, Scenario(topic="absent")) == []
    contacted = replace(graph, contacts={**graph.contacts, "x": "2026-08-15"})
    assert [r["person_id"] for r in expected_answer(contacted, Scenario())] == ["y"]
    assert expected_answer(graph, Scenario(kind="lookup")) == [{"person_id": "r", "topic": "graphs"}]


def test_equal_length_path_tie_chooses_lexicographic_representative():
    graph = known_graph()
    extra = dict(source="a", target="y", kind="collaborated", last_seen="2026-07-01")
    other = dict(source="y", target="z", kind="collaborated", last_seen="2026-07-01")
    first = dict(source="c", target="z", kind="collaborated", last_seen="2026-07-01")
    graph = replace(graph, edges=graph.edges + (extra, other, first))
    z = next(r for r in expected_answer(graph, Scenario()) if r["person_id"] == "z")
    assert z["paths"] == [["r", "a", "c", "z"]]


def test_api_filters_projection_copies_and_failures_are_observable():
    api = GraphAPI(known_graph(), max_calls=5)
    assert api.execute("neighbors", ["b"], kind="collaborated", since="2026-01-01") == [
        {"source": "b", "target": "x", "kind": "collaborated", "last_seen": "2026-07-01"}]
    profile = api.execute("profiles", ["x"], fields=["topic"])
    assert profile == [{"person_id": "x", "topic": "graphs"}]
    profile[0]["topic"] = "changed"
    assert api.data.profiles["x"]["topic"] == "graphs"
    assert api.execute("contacts", ["c", "x"], since="2026-08-01") == [
        {"person_id": "c", "last_contact": "2026-08-01"}]
    with pytest.raises(ValueError, match="distinct known"):
        api.execute("profiles", ["missing"], fields=["topic"])
    with pytest.raises(ValueError, match="distinct known"):
        api.execute("profiles", ["x", "x"], fields=["topic"])
    with pytest.raises(ValueError, match="budget"):
        api.execute("profiles", ["x"], fields=["topic"])
    assert [c["ok"] for c in api.calls] == [True, True, True, False, False, False]
    assert all("elapsed_seconds" in row for row in api.calls)


def test_fixtures_and_cases_separate_depth_from_graph_size():
    assert make_graph(10) == make_graph(10)
    assert make_graph(10) != make_graph(11)
    assert CASES[1].width == CASES[2].width and CASES[1].depth != CASES[2].depth
    assert CASES[2].depth == CASES[3].depth and CASES[2].width != CASES[3].width
    assert len(make_graph(10, 12).profiles) > len(make_graph(10, 6).profiles)
    assert len(set(arm_order(i) for i in range(6))) == 6
    for case_index in range(len(CASES)):
        assert arm_order(2 * case_index) == arm_order(2 * case_index + 1)[::-1]
    assert Config().planned_runs == 24
    with pytest.raises(ValueError):
        Config(seeds=(1, 1))
    with pytest.raises(ValueError):
        Config(cases=(Scenario(), Scenario()))


def test_read_evidence_rejects_lucky_empty_answers_and_allows_pruning():
    data = known_graph()
    api, case = GraphAPI(data), Scenario(topic="absent")
    api.execute("neighbors", ["r"], kind="collaborated", since=case.edge_since)
    assert expected_answer(data, case) == []
    assert not sufficient_reads(api, case, [])
    api.execute("neighbors", list(data.profiles), kind="collaborated", since=case.edge_since)
    assert not sufficient_reads(api, case, [])  # Candidate topics are still unknown.
    api.execute("profiles", list(data.profiles), fields=["topic"])
    assert sufficient_reads(api, case, [])  # No contact reads needed: all wrong topic.

    api, case = GraphAPI(data), Scenario(limit=1)
    api.execute("neighbors", list(data.profiles), kind="collaborated", since=case.edge_since)
    api.execute("profiles", ["x"], fields=["topic"])
    assert not sufficient_reads(api, case, expected_answer(data, case))
    api.execute("contacts", ["x"], since=case.contact_since)
    assert sufficient_reads(api, case, expected_answer(data, case))  # Lower-ranked people pruned.


def test_concurrency_limit_applies_to_parallel_api_reads(monkeypatch):
    import asyncio
    import time
    from threading import Lock

    api = GraphAPI(known_graph(), concurrency=2)
    original, lock = api.execute, Lock()
    active = peak = 0

    def slow(*args, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.01)
            return original(*args, **kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(api, "execute", slow)

    async def run():
        return await asyncio.gather(*(api.read("profiles", ["x"], fields=["topic"]) for _ in range(8)))

    assert len(asyncio.run(run())) == 8
    assert peak == 2 and len(api.calls) == 8
