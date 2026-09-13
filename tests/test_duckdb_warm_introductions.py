"""Behavioral checks for the synthetic path task and its two real tool routes."""

import asyncio
from dataclasses import replace
import json
from pathlib import Path

import pytest

pytest.importorskip("duckdb")
pytest.importorskip("langchain_quickjs")
import duckdb
from langchain_core.messages import AIMessage
from langsmith import tracing_context

from deepagents_lab.experiments.duckdb_warm_introductions.domain import Question
from deepagents_lab.experiments.duckdb_warm_introductions.fixture import create_fixture, make_network
from deepagents_lab.experiments.duckdb_warm_introductions.oracle import expected_routes
from deepagents_lab.experiments.duckdb_warm_introductions.prompts import task_prompt
from deepagents_lab.experiments.duckdb_warm_introductions.reference import REFERENCE_SQL, named_rows, reference_parameters
from deepagents_lab.experiments.duckdb_warm_introductions.smoke import ScriptedModel, executed_answer, scripted_model
from deepagents_lab.experiments.duckdb_warm_introductions.tools import NetworkTools
from deepagents_lab.experiments.duckdb_warm_introductions.trial import grade, run_trial


def sql_answer(path, question):
    result = NetworkTools(path).query(REFERENCE_SQL, reference_parameters(question))
    assert result["ok"], result
    return {"routes": named_rows(result)}


def test_explicit_paths_and_distractors(tmp_path):
    network, question = make_network(), Question(top_k=10)
    path = create_fixture(tmp_path / "network.duckdb", network)
    expected = expected_routes(network, question)
    assert sql_answer(path, question) == expected
    routes = expected["routes"]
    assert [r["path"] for r in routes] == [
        ["user", "vera"], ["user", "maya", "leo"], ["user", "chris", "nina"],
        ["user", "ari", "sam", "leo"], ["user", "hub", "hub-employee-0000"],
    ]
    assert [r["bottleneck_strength"] for r in routes] == [5, 5, 4, 4, 1]
    assert routes[1]["evidence_ids"] == ["rel-user-maya", "rel-maya-leo"]
    assert routes[1]["employment_evidence_id"] == "emp-leo"
    assert routes[1]["oldest_evidence_at"] == "2026-08-01"
    # Even the expanded top-k excludes former/wrong-team/future/stale/reverse-only/
    # affiliation-only contacts; the hub contributes exactly one weak route.
    assert len({r["connector_id"] for r in routes}) == len(routes)
    assert all(len(set(r["path"])) == len(r["path"]) for r in routes)


@pytest.mark.parametrize("question,connectors", [
    (Question(max_hops=1), ["vera"]),
    (Question(max_hops=2), ["vera", "maya", "chris", "hub"]),
    (Question(cutoff="2026-09-01"), ["ari", "hub"]),
    (Question(cutoff="2026-09-13"), []),
    (Question(user_id="leo"), []),
])
def test_depth_recency_and_empty_results(tmp_path, question, connectors):
    network = make_network()
    path = create_fixture(tmp_path / "network.duckdb", network)
    answer = sql_answer(path, question)
    assert answer == expected_routes(network, question)
    assert [r["connector_id"] for r in answer["routes"]] == connectors


def test_runtime_employment_update_and_date_boundaries(tmp_path):
    network, question = make_network(), Question()
    path = create_fixture(tmp_path / "network.duckdb", network)
    assert sql_answer(path, question)["routes"][0]["connector_id"] == "vera"
    # An end date equal to as_of is already ineligible. The next read must see it.
    with duckdb.connect(str(path)) as connection:
        connection.execute("UPDATE employment SET ends_at = ? WHERE person_id = 'vera'", [question.as_of])
    changed = replace(network, employment=tuple(
        replace(e, ends_at=question.as_of) if e.person_id == "vera" else e for e in network.employment
    ))
    answer = sql_answer(path, question)
    assert answer == expected_routes(changed, question)
    assert [r["connector_id"] for r in answer["routes"]] == ["maya", "chris", "ari", "hub"]
    # Both recency endpoints and the employment start date are inclusive.
    boundary = replace(network,
        relationships=tuple(replace(e, observed_at=question.cutoff) for e in network.relationships),
        employment=tuple(replace(e, starts_at=question.as_of) for e in network.employment),
    )
    second = create_fixture(tmp_path / "boundary.duckdb", boundary)
    assert sql_answer(second, question) == expected_routes(boundary, question)
    assert sql_answer(second, question)["routes"][0]["connector_id"] == "not-started"


@pytest.mark.parametrize("sql", [
    "DELETE FROM relationships",
    "SELECT 1; SELECT 2",
    "SELECT * FROM range(101)",
    "SELECT repeat('x', 21000)",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT nonexistent_column FROM people",
])
def test_recoverable_sql_errors_and_limits(tmp_path, sql):
    bridge = NetworkTools(create_fixture(tmp_path / "network.duckdb", make_network()))
    assert bridge.query(sql)["ok"] is False
    assert bridge.query("SELECT COUNT(*) FROM people")["ok"] is True
    assert len(bridge.calls) == 2
    assert bridge.calls[0]["result"]["error"]


def test_attempt_budget_counts_schema_and_errors(tmp_path):
    bridge = NetworkTools(create_fixture(tmp_path / "network.duckdb", make_network()), max_calls=2)
    assert bridge.tools()[0].invoke({})["ok"]
    assert not bridge.query("SELECT missing FROM people")["ok"]
    assert "budget" in bridge.query("SELECT 1")["error"]
    assert len(bridge.database.queries) == 2  # The over-budget query never reaches DuckDB.


@pytest.mark.parametrize("arm", ["ordinary", "interpreter"])
@pytest.mark.parametrize("inject_error", [False, True])
def test_real_agent_tools_return_the_expected_evidence(tmp_path, arm, inject_error):
    network, question = make_network(), Question()
    path = create_fixture(tmp_path / "network.duckdb", network)
    expected = expected_routes(network, question)
    with tracing_context(enabled=False):
        record = asyncio.run(run_trial(
            scripted_model(arm, question, expected, inject_error=inject_error),
            arm, path, task_prompt(question), expected, log_path=tmp_path / "trial.json",
        ))
    assert record["correct"], record
    assert executed_answer(record) == expected  # Actual ToolMessage, not fake final text.
    assert record["sql_attempts"] == 2 + inject_error
    assert record["sql_errors"] == int(inject_error)
    assert record["total_tokens"] is None and not record["usage_complete"]
    assert record["elapsed_seconds"] > 0
    assert json.loads((tmp_path / "trial.json").read_text()) == record


def test_validator_rejects_unqueried_or_fabricated_answers():
    expected = {"routes": []}
    assert not grade(json.dumps(expected), expected, "ordinary", [], [])['route_correct']
    calls = [{"kind": "query", "result": {"ok": True}}]
    model_calls = [{"tool_names": ["query_duckdb"]}]
    assert not grade('{"routes": [{"path": ["invented"]}]}', expected, "ordinary", calls, model_calls)['answer_correct']
    assert not grade(json.dumps(expected), expected, "interpreter", calls, model_calls)['route_correct']


def test_failed_model_attempt_keeps_queries_and_partial_usage(tmp_path):
    class FailAfterQuery(ScriptedModel):
        async def _agenerate(self, *args, **kwargs):
            if self.i == 1:
                raise RuntimeError("deliberate provider failure")
            return await super()._agenerate(*args, **kwargs)

    response = AIMessage(content="", tool_calls=[{
        "name": "query_duckdb", "args": {"sql": "SELECT COUNT(*) FROM relationships"},
        "id": "probe", "type": "tool_call",
    }], usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120})
    model = FailAfterQuery(responses=[response, AIMessage(content="unreachable")])
    path = create_fixture(tmp_path / "network.duckdb", make_network())
    with tracing_context(enabled=False):
        record = asyncio.run(run_trial(model, "ordinary", path, "Probe the data", {"routes": []},
                                       mode="live", log_path=tmp_path / "failed.json"))
    assert not record["correct"]
    assert record["error"]["message"] == "deliberate provider failure"
    assert record["model_calls"] == 2 and record["sql_attempts"] == 1
    assert not record["usage_complete"] and record["total_tokens"] is None
    assert record["model_call_details"][0]["usage"]["total_tokens"] == 120
    assert record["model_call_details"][1]["error_type"] == "RuntimeError"
    assert json.loads((tmp_path / "failed.json").read_text())["error"] == record["error"]


def test_latency_excludes_cleanup_inside_ainvoke(tmp_path, monkeypatch):
    from langchain_quickjs import CodeInterpreterMiddleware

    original = CodeInterpreterMiddleware.aafter_agent
    cleanup_calls = []

    async def slow_cleanup(self, state, runtime):
        # Make a known cleanup cost observable without relying on machine speed.
        cleanup_calls.append(bool(state.get("messages")))
        await asyncio.sleep(0.1)
        return await original(self, state, runtime)

    monkeypatch.setattr(CodeInterpreterMiddleware, "aafter_agent", slow_cleanup)
    network, question = make_network(), Question()
    path = create_fixture(tmp_path / "network.duckdb", network)
    expected = expected_routes(network, question)
    with tracing_context(enabled=False):
        record = asyncio.run(run_trial(
            scripted_model("interpreter", question, expected), "interpreter",
            path, task_prompt(question), expected,
        ))
    assert record["correct"] and executed_answer(record) == expected
    assert cleanup_calls == [True, False]  # Automatic eviction, then fallback.
    assert record["interpreter_cleanup_seconds"] >= 0.1
    assert record["invocation_wall_seconds"] - record["elapsed_seconds"] == pytest.approx(
        record["interpreter_cleanup_seconds"], abs=0.001,
    )
    assert record["elapsed_seconds"] > 0
