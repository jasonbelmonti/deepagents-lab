from __future__ import annotations

import asyncio
import json
import sqlite3
import subprocess
import sys

import pytest
from langchain_core.messages import AIMessage

from deepagents_lab.experiments.graph_workspace.fixture import create_fixture
from deepagents_lab.experiments.graph_workspace.runner import PROGRAM, RecipeModel, compare, run_probe
from deepagents_lab.experiments.graph_workspace.store import GraphStore, Query, StaleRevision, WorkBudgetExceeded


@pytest.fixture
def store(tmp_path):
    return create_fixture(tmp_path / "graph.sqlite", people=1000)


def test_native_query_returns_exact_fixture_paths_and_filters(store):
    assert store.answer(Query(), 1) == [
        {"person_id": "p000003", "path": ["p000000", "p000001", "p000003"]},
        {"person_id": "p000006", "path": ["p000000", "p000002", "p000006"]},
        {"person_id": "p000009", "path": ["p000000", "p000001", "p000004", "p000009"]},
        {"person_id": "p000012", "path": ["p000000", "p000002", "p000005", "p000012"]},
    ]
    assert not store.answer(Query(since="2027-01-01"), 1)
    assert not store.answer(Query(root="missing"), 1)
    assert not store.answer(Query(root="p000030"), 1), "Directed paths must not traverse backwards."


@pytest.mark.parametrize("mode", ["turn", "thread"])
def test_real_ptc_materialization_arms_agree_and_bound_transfer(store, mode):
    pytest.importorskip("langchain_quickjs")
    rows = [asyncio.run(run_probe(store, Query(), arm, mode=mode)) for arm in ("eager", "bounded", "backend")]
    assert all(row["valid"] for row in rows), rows
    assert all(row["answers"] == store.answer(Query(), 1) for row in rows)
    assert rows[0]["response_bytes"] > rows[1]["response_bytes"] > rows[2]["response_bytes"]
    assert all(row["model_calls"] is None and row["total_tokens"] is None for row in rows)
    if mode == "turn":
        assert all(row["snapshot_bytes"] == 0 for row in rows)
    else:
        assert rows[0]["snapshot_bytes"] > rows[1]["snapshot_bytes"] > 0


@pytest.mark.parametrize("program", ["JSON.stringify([]);", PROGRAM + "\nunknownVariable;", PROGRAM + "\nJSON.stringify([]);"])
def test_invalid_interpreter_work_is_not_valid_efficiency_evidence(store, program):
    pytest.importorskip("langchain_quickjs")
    row = asyncio.run(run_probe(store, Query(), "bounded", program=program))
    assert not row["valid"]


def test_transfer_and_database_work_budgets_fail_explicitly(store):
    pytest.importorskip("langchain_quickjs")
    row = asyncio.run(run_probe(store, Query(), "eager", byte_budget=1))
    assert not row["valid"] and row["tool_calls"][0]["error_type"] == "WorkBudgetExceeded"
    limited = GraphStore(store.path, vm_budget=100)
    with pytest.raises(WorkBudgetExceeded):
        limited.answer(Query(), 1)
    row = asyncio.run(run_probe(limited, Query(), "backend"))
    assert not row["valid"] and row["phase"] == "oracle"


def test_persistence_update_retry_and_explicit_refresh_in_new_process(store):
    store.save_investigation("intro", Query(), 1)
    original = store.answer(Query(), 1)
    revision = store.remove_edge("p000000", "p000001", expected_revision=1, operation_id="remove-1")
    assert revision == 2
    assert store.remove_edge("p000000", "p000001", expected_revision=1, operation_id="remove-1") == 2
    assert store.revision == 2
    with pytest.raises(ValueError, match="different request"):
        store.remove_edge("p000000", "p000002", expected_revision=1, operation_id="remove-1")
    with pytest.raises(StaleRevision):
        store.remove_edge("p000000", "p000002", expected_revision=1, operation_id="remove-2")
    code = """
import json, sys
from pathlib import Path
from deepagents_lab.experiments.graph_workspace.store import GraphStore, StaleRevision
s = GraphStore(Path(sys.argv[1]))
q, saved = s.load_investigation('intro')
try:
    s.answer(q, saved)
except StaleRevision:
    pass
else:
    raise AssertionError('stale revision was accepted')
print(json.dumps(s.answer(q, s.revision)))
"""
    result = subprocess.run([sys.executable, "-c", code, str(store.path)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) != original
    assert store.load_investigation("intro")[1] == 1, "Refreshing is not an implicit mutation of saved history."


def test_growth_outside_neighborhood_does_not_grow_bounded_view(tmp_path):
    stores = [create_fixture(tmp_path / f"{size}.sqlite", people=size) for size in (100, 10_000)]
    views = [s.materialize(Query(), 1, bounded=True) for s in stores]
    assert views[0] == views[1]
    hub = create_fixture(tmp_path / "hub.sqlite", people=1000, hub_edges=10)
    assert len(hub.materialize(Query(), 1, bounded=True)["people"]) > len(views[0]["people"])
    with pytest.raises(WorkBudgetExceeded):
        hub.materialize(Query(), 1, bounded=True, row_limit=5)


def test_read_transaction_rejects_stale_revision_and_never_recreates_missing_file(store, tmp_path):
    with pytest.raises(StaleRevision):
        store.materialize(Query(), 99, bounded=False)
    with pytest.raises(FileNotFoundError):
        GraphStore(tmp_path / "missing.sqlite")
    assert not (tmp_path / "missing.sqlite").exists()
    with pytest.raises(FileExistsError):
        create_fixture(store.path)


def test_cycles_and_path_ties_match_sql_and_js(store):
    pytest.importorskip("langchain_quickjs")
    with sqlite3.connect(store.path) as db:
        db.executemany("INSERT INTO edges VALUES (?, ?, 'collaborated', '2026-01-01')", [
            ("p000003", "p000000"), ("p000002", "p000003"),
        ])
    row = asyncio.run(run_probe(store, Query(), "bounded"))
    assert row["valid"]
    assert row["answers"][0]["path"] == ["p000000", "p000001", "p000003"]


def test_repeated_comparison_rotates_order_and_retains_rows(store):
    pytest.importorskip("langchain_quickjs")
    rows = asyncio.run(compare(store, Query(), repeats=3))
    assert [r["arm"] for r in rows] == ["eager", "bounded", "backend", "bounded", "backend", "eager", "backend", "eager", "bounded"]
    assert all(r["valid"] for r in rows)


@pytest.mark.parametrize("defect", ["none", "missing_usage", "wrong_final"])
def test_live_path_requires_actual_usage_and_exact_final_answer(store, monkeypatch, defect):
    pytest.importorskip("langchain_quickjs")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    responses = [
        AIMessage(content="", tool_calls=[{"name": "eval", "args": {"code": PROGRAM}, "id": "live-test", "type": "tool_call"}]),
        AIMessage(content=json.dumps(store.answer(Query(), 1))),
    ]
    for response in responses:
        response.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    if defect == "missing_usage":
        responses[-1].usage_metadata = None
    elif defect == "wrong_final":
        responses[-1].content = "[]"
    row = asyncio.run(run_probe(store, Query(), "bounded", model=RecipeModel(responses=responses)))
    assert row["valid"] is (defect == "none")
    assert row["model_calls"] == 2
    assert row["total_tokens"] == (None if defect == "missing_usage" else 240)


def test_update_during_investigation_invalidates_old_result(store, monkeypatch):
    pytest.importorskip("langchain_quickjs")
    materialize = store.materialize

    def read_then_update(*args, **kwargs):
        value = materialize(*args, **kwargs)
        store.remove_edge("p000000", "p000001", expected_revision=1, operation_id="interleaved")
        return value

    monkeypatch.setattr(store, "materialize", read_then_update)
    row = asyncio.run(run_probe(store, Query(), "bounded"))
    assert row["revision"] == 1 and store.revision == 2
    assert not row["valid"], "Correct old answers cannot masquerade as current answers."


def test_short_read_transaction_stays_consistent_during_a_write(store):
    with store.read(1) as db:
        store.remove_edge("p000000", "p000001", expected_revision=1, operation_id="parallel-write")
        assert db.execute("SELECT revision FROM metadata").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM edges WHERE source='p000000' AND target='p000001'").fetchone()[0] == 1
    assert store.revision == 2
