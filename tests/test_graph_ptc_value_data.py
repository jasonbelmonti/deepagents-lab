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
    assert [c["delivered"] for c in api.calls] == [True, True, True, False, False, False]
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


def test_profile_field_reuse_cannot_rewrite_past_read_evidence():
    data, case = known_graph(), Scenario(kind="lookup")
    api = GraphAPI(data)
    fields = ["name"]
    assert api.execute("profiles", ["r"], fields=fields) == [{"person_id": "r", "name": "r"}]
    assert not sufficient_reads(api, case, expected_answer(data, case))
    fields.append("topic")
    api.execute("profiles", ["x"], fields=fields)
    assert not sufficient_reads(api, case, expected_answer(data, case))
    api.execute("profiles", ["r"], fields=fields)
    fields.remove("topic")
    assert sufficient_reads(api, case, expected_answer(data, case))
    assert api.calls[0]["options"]["fields"] == ["name"]
    assert api.calls[-1]["options"]["fields"] == ["name", "topic"]


def contact_graph(last_contact):
    data = known_graph()
    edges = tuple(e for e in data.edges if (e["source"], e["target"]) in {("r", "a"), ("a", "x")})
    return replace(data, edges=edges, contacts={} if last_contact is None else {"x": last_contact})


@pytest.mark.parametrize("query_since", ["2026-07-01", "2026-08-01", "2026-08-10"])
def test_returned_recent_contact_proves_exclusion(query_since):
    data, case = contact_graph("2026-08-15"), Scenario(depth=2)
    api = GraphAPI(data)
    api.execute("neighbors", ["r", "a"], kind="collaborated", since=case.edge_since)
    assert api.execute("contacts", ["x"], since=query_since) == [
        {"person_id": "x", "last_contact": "2026-08-15"}]
    assert expected_answer(data, case) == []
    assert sufficient_reads(api, case, [])  # No topic read or redundant contact query needed.


@pytest.mark.parametrize("last_contact", ["2026-08-05", "2026-07-15", None])
def test_later_empty_contact_query_cannot_establish_absence(last_contact):
    data, case = contact_graph(last_contact), Scenario(depth=2)
    api = GraphAPI(data)
    api.execute("neighbors", ["r", "a"], kind="collaborated", since=case.edge_since)
    api.execute("profiles", ["x"], fields=["topic"])
    assert api.execute("contacts", ["x"], since="2026-08-10") == []
    assert not sufficient_reads(api, case, expected_answer(data, case))
    api.execute("contacts", ["x"], since=case.contact_since)
    assert sufficient_reads(api, case, expected_answer(data, case))


def test_returned_old_contact_does_not_prove_exclusion():
    data, case = contact_graph("2026-07-15"), Scenario(depth=2)
    api = GraphAPI(data)
    api.execute("neighbors", ["r", "a"], kind="collaborated", since=case.edge_since)
    assert api.execute("contacts", ["x"], since="2026-07-01") == [
        {"person_id": "x", "last_contact": "2026-07-15"}]
    assert expected_answer(data, case)
    assert not sufficient_reads(api, case, expected_answer(data, case))  # Topic still unknown.
    api.execute("profiles", ["x"], fields=["topic"])
    assert sufficient_reads(api, case, expected_answer(data, case))


def test_complete_root_read_can_prove_connector_minimum_impossible():
    data, case = known_graph(), Scenario(min_connectors=3)
    api = GraphAPI(data)
    assert expected_answer(data, case) == []
    assert not sufficient_reads(api, case, [])
    api.execute("neighbors", ["r"], kind="follows", since=case.edge_since)
    api.execute("neighbors", ["r"], kind="collaborated", since="2026-08-01")
    assert not sufficient_reads(api, case, [])  # Neither query covers the requested edges.
    api.execute("neighbors", ["r"], kind="collaborated", since=case.edge_since)
    assert sufficient_reads(api, case, [])  # Only two possible first-hop connectors.
    lower_minimum = replace(case, min_connectors=2)
    assert expected_answer(data, lower_minimum)
    assert not sufficient_reads(api, lower_minimum, expected_answer(data, lower_minimum))


@pytest.mark.parametrize("first_fails", [False, True])
def test_cancelled_read_keeps_capacity_until_worker_finishes(monkeypatch, first_fails):
    import asyncio
    from contextvars import ContextVar
    from threading import Event, Lock

    api = GraphAPI(known_graph(), concurrency=1)
    original, lock = api._execute, Lock()
    release_first, first_started, second_started = Event(), Event(), Event()
    context = ContextVar("graph_read_test_context")
    active = peak = 0

    def gated(name, ids, **options):
        nonlocal active, peak
        assert context.get() == "caller"
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            if ids != ["x"]:
                first_started.set()
                assert release_first.wait(3), "First worker was not released"
            else:
                second_started.set()
            return original(name, ids, **options)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(api, "_execute", gated)

    async def run():
        context.set("caller")
        first = asyncio.create_task(api.read("profiles", ["missing" if first_fails else "r"], fields=["topic"]))
        second = None
        try:
            async with asyncio.timeout(2):
                while not first_started.is_set():
                    await asyncio.sleep(0.001)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            second = asyncio.create_task(api.read("profiles", ["x"], fields=["topic"]))
            await asyncio.sleep(0.05)
            assert not second_started.is_set()
            release_first.set()
            assert await asyncio.wait_for(second, 2) == [{"person_id": "x", "topic": "graphs"}]
        finally:
            release_first.set()
            await asyncio.gather(*(task for task in (first, second) if task is not None), return_exceptions=True)

    asyncio.run(run())
    assert peak == 1
    assert [row["ok"] for row in api.calls] == [not first_fails, True]
    assert [row["delivered"] for row in api.calls] == [False, True]
    assert not sufficient_reads(api, Scenario(kind="lookup"), expected_answer(api.data, Scenario(kind="lookup")))
    if first_fails:
        assert api.calls[0]["error_type"] == "ValueError"


@pytest.mark.parametrize("proof", ["lookup", "connector-bound", "contact-exclusion", "contact-absence"])
def test_cancelled_result_is_accounted_but_not_read_evidence(proof):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    data = contact_graph("2026-08-15" if proof == "contact-exclusion" else None)
    case = Scenario(kind="lookup") if proof == "lookup" else Scenario(depth=2)
    api = GraphAPI(data)
    if proof == "lookup":
        name, ids, options = "profiles", ["r"], {"fields": ["topic"]}
    elif proof == "connector-bound":
        case = replace(case, min_connectors=2)
        name, ids, options = "neighbors", ["r"], {"kind": "collaborated", "since": case.edge_since}
    else:
        api.execute("neighbors", ["r", "a"], kind="collaborated", since=case.edge_since)
        if proof == "contact-absence":
            api.execute("profiles", ["x"], fields=["topic"])
        name, ids, options = "contacts", ["x"], {"since": case.contact_since}
    expected = expected_answer(data, case)
    assert not sufficient_reads(api, case, expected)
    prior_calls = len(api.calls)

    async def run():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        release = Event()
        occupied = loop.run_in_executor(None, release.wait)
        caller = asyncio.create_task(api.read(name, ids, **options))
        try:
            await asyncio.sleep(0)  # Queue the real read behind the occupied worker.
            assert len(api.calls) == prior_calls
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller
        finally:
            release.set()
            await occupied
            await asyncio.gather(caller, return_exceptions=True)
        await loop.run_in_executor(None, lambda: None)  # Drain queued work.
        assert caller.cancelled()
        assert len(api.calls) == prior_calls + 1
        cancelled = api.calls[-1]
        assert cancelled["ok"] and cancelled["response_bytes"] > 0
        assert "records" in cancelled and "elapsed_seconds" in cancelled
        assert not sufficient_reads(api, case, expected)
        assert cancelled["delivered"] is False

        result = await api.read(name, ids, **options)
        assert result == GraphAPI(data).execute(name, ids, **options)
        assert sufficient_reads(api, case, expected)
        assert api.calls[-1]["delivered"] is True
        assert cancelled["delivered"] is False  # A retry cannot rewrite the old receipt.

    asyncio.run(run())


def test_concurrency_limit_applies_to_parallel_api_reads(monkeypatch):
    import asyncio
    import time
    from threading import Lock

    api = GraphAPI(known_graph(), concurrency=2)
    original, lock = api._execute, Lock()
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

    monkeypatch.setattr(api, "_execute", slow)

    async def run():
        return await asyncio.gather(*(api.read("profiles", ["x"], fields=["topic"]) for _ in range(8)))

    assert len(asyncio.run(run())) == 8
    assert peak == 2 and len(api.calls) == 8
    assert all(row["delivered"] for row in api.calls)
