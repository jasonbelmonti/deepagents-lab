from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from deepagents import create_deep_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from deepagents_lab.benchmarks.incident_fixture import STAGES, IncidentFixture
from deepagents_lab.benchmarks.incident_metrics import ModelMeasurements, validate_trial
from deepagents_lab.benchmarks.incident_report import percentile, summarize
from deepagents_lab.benchmarks.incident_triage import BenchmarkConfig, model_settings, run_benchmark


def complete_fixture(fixture: IncidentFixture) -> list[list[dict[str, Any]]]:
    stages = [fixture.execute(0, fixture.ids)]
    for stage, key in enumerate(("evidence_ref", "context_ref", "decision_ref"), start=1):
        stages.append(fixture.execute(stage, [row[key] for row in stages[-1]]))
    return stages


def test_fixture_size_dependencies_and_exact_coverage() -> None:
    fixture = IncidentFixture()
    stages = complete_fixture(fixture)
    assert all(len(json.dumps(row).encode()) == 1536 for rows in stages[:3] for row in rows)
    assert fixture.coverage_ok()
    assert len(stages[-1]) == 20
    assert len(fixture.expected) == 9
    fixture.execute(0, fixture.ids)
    assert not fixture.coverage_ok(), "Repeated work must not masquerade as the same workload."

    fresh = IncidentFixture()
    with pytest.raises(ValueError, match="preceding stage"):
        fresh.execute(1, [row["evidence_ref"] for row in stages[0]])
    assert not fresh.coverage_ok()


def add_response(callback: ModelMeasurements, run: str, tokens: dict[str, Any] | None) -> None:
    callback.on_chat_model_start({}, [], run_id=run)
    callback.on_llm_end(
        LLMResult(generations=[[ChatGeneration(message=AIMessage(
            content="done", usage_metadata=tokens, response_metadata={"model_name": "test"},
        ))]]), run_id=run,
    )


def test_accounting_sums_all_calls_and_preserves_unknown_usage() -> None:
    callback = ModelMeasurements()
    for run in ("first", "second"):
        add_response(callback, run, {
            "input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
            "input_token_details": {"cache_read": 40}, "output_token_details": {"reasoning": 5},
        })
    totals = callback.totals()
    assert totals["model_calls"] == 2
    assert (totals["input_tokens"], totals["output_tokens"], totals["total_tokens"]) == (200, 40, 240)
    assert (totals["cache_read_tokens"], totals["reasoning_tokens"]) == (80, 10)
    add_response(callback, "missing", None)
    assert callback.totals()["total_tokens"] is None
    assert not callback.totals()["usage_complete"]


def test_explicit_openai_client_preserves_responses_default() -> None:
    assert model_settings(BenchmarkConfig()) == {
        "timeout": 90, "max_retries": 0, "use_responses_api": True,
    }


def test_validation_rejects_inexact_answers_and_wrong_path() -> None:
    fixture = IncidentFixture()
    complete_fixture(fixture)
    callback = ModelMeasurements()
    add_response(callback, "one", {"input_tokens": 2, "output_tokens": 2, "total_tokens": 4})
    callback.calls["one"]["tool_names"] = ["eval"]
    result = {"messages": [AIMessage(content=json.dumps(fixture.expected))]}
    assert validate_trial(result, fixture, callback, "ptc")["valid"]
    assert not validate_trial(result, fixture, callback, "ordinary")["valid"]
    for incorrect in (fixture.expected[:-1], fixture.expected[::-1], fixture.expected + [fixture.decisions[0]]):
        result["messages"] = [AIMessage(content=json.dumps(incorrect))]
        assert not validate_trial(result, fixture, callback, "ptc")["valid"]
    wrong_owner = [dict(row, owner="wrong") for row in fixture.expected]
    result["messages"] = [AIMessage(content=json.dumps(wrong_owner))]
    assert not validate_trial(result, fixture, callback, "ptc")["valid"]


def test_alternating_pairs_preserve_failures_and_write_incrementally(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from deepagents_lab.benchmarks import incident_triage

    seen = []

    async def fake_trial(config: Any, arm: str, pair: int, position: int) -> dict[str, Any]:
        if seen:
            saved = json.loads(next(tmp_path.glob("*/report.json")).read_text())
            assert len(saved["trials"]) == len(seen)
        seen.append((pair, arm))
        return {
            "pair": pair, "arm": arm, "position": position, "valid": not (pair == 2 and arm == "ptc"),
            "elapsed_seconds": float(pair), "model_calls": 2, "input_tokens": 10,
            "output_tokens": 5, "total_tokens": 15, "cache_read_tokens": None, "reasoning_tokens": None,
        }

    monkeypatch.setattr(incident_triage, "run_trial", fake_trial)
    # The runner's control flow is independent of optional package installation.
    monkeypatch.setattr(incident_triage, "version", lambda _: "test-version")
    report = asyncio.run(run_benchmark(BenchmarkConfig(), tmp_path, progress=lambda _: None))
    assert seen == [(pair, arm) for pair in range(1, 6) for arm in (
        ("ordinary", "ptc") if pair % 2 else ("ptc", "ordinary")
    )]
    assert len(report["trials"]) == 10
    summary = summarize(report["trials"])
    assert summary["valid_pairs"] == 4
    assert summary["invalid_trials"] == 1
    assert summary["ordinary"]["latency_p50_seconds"] == 3.5  # Pair 2 excluded from both arms.
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5


def test_repeated_request_failures_stop_without_losing_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from deepagents_lab.benchmarks import incident_triage

    async def failed_trial(config: Any, arm: str, pair: int, position: int) -> dict[str, Any]:
        return {
            "pair": pair, "arm": arm, "position": position, "valid": False,
            "elapsed_seconds": 0.5, "model_calls": 1, "input_tokens": None,
            "output_tokens": None, "total_tokens": None, "cache_read_tokens": None,
            "reasoning_tokens": None, "error_type": "RequestError", "error_status": 400,
        }

    monkeypatch.setattr(incident_triage, "run_trial", failed_trial)
    monkeypatch.setattr(incident_triage, "version", lambda _: "test-version")
    report = asyncio.run(run_benchmark(BenchmarkConfig(), tmp_path, progress=lambda _: None))
    saved = json.loads(Path(report["report_path"]).read_text())
    assert len(saved["trials"]) == 2
    assert saved["stop_reason"]
    assert saved["summary"]["valid_pairs"] == 0


class ScriptedToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedToolModel:
        return self


@pytest.mark.parametrize("arm", ["ordinary", "ptc"])
def test_real_graph_and_quickjs_execute_all_four_stages_offline(arm: str) -> None:
    quickjs = pytest.importorskip("langchain_quickjs")
    fixture = IncidentFixture()
    expected_fixture = IncidentFixture()
    stages = complete_fixture(expected_fixture)
    if arm == "ordinary":
        input_keys = ("incident_ids", "evidence_refs", "context_refs", "decision_refs")
        reference_keys = ("evidence_ref", "context_ref", "decision_ref")
        calls = [
            (name, {input_keys[index]: fixture.ids if index == 0 else [
                row[reference_keys[index - 1]] for row in stages[index - 1]
            ]})
            for index, name in enumerate(STAGES)
        ]
        middleware = []
    else:
        code = f"""
const incidents = await tools.fetchIncidents({{incident_ids: {json.dumps(fixture.ids)}}});
const evidence = await tools.fetchEvidence({{evidence_refs: incidents.map(x => x.evidence_ref)}});
const context = await tools.fetchServiceContext({{context_refs: evidence.map(x => x.context_ref)}});
const decisions = await tools.classifyIncidents({{decision_refs: context.map(x => x.decision_ref)}});
JSON.stringify(decisions.filter(x => x.priority !== 'P3').sort((a, b) =>
    a.priority.localeCompare(b.priority) || a.incident_id.localeCompare(b.incident_id)));
"""
        calls = [("eval", {"code": code})]
        middleware = [quickjs.CodeInterpreterMiddleware(ptc=fixture.tools(), subagents=False, mode="call")]
    responses = [AIMessage(content="", tool_calls=[{
        "name": name, "args": args, "id": f"call-{index}", "type": "tool_call",
    }]) for index, (name, args) in enumerate(calls)]
    responses.append(AIMessage(content=json.dumps(fixture.expected)))
    for response in responses:
        response.usage_metadata = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    measurements = ModelMeasurements()
    graph = create_deep_agent(model=ScriptedToolModel(responses=responses), tools=fixture.tools(), middleware=middleware)
    result = asyncio.run(graph.ainvoke({"messages": [{"role": "user", "content": "Run triage."}]}, config={
        "callbacks": [measurements], "configurable": {"thread_id": f"offline-{arm}"},
    }))
    assert validate_trial(result, fixture, measurements, arm)["valid"]
    assert len(fixture.calls) == 4
    assert measurements.totals()["model_calls"] == (5 if arm == "ordinary" else 2)
