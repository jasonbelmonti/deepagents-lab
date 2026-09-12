"""Accounting regressions use real graph/QuickJS execution, never provider calls."""
from __future__ import annotations

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage

from deepagents_lab.experiments.graph_workspace.fixture import create_fixture
from deepagents_lab.experiments.graph_workspace.runner import PROGRAM, RecipeModel, run_probe
from deepagents_lab.experiments.graph_workspace.store import Query

pytest.importorskip("langchain_quickjs")


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    store = create_fixture(tmp_path / "graph.sqlite", people=31)
    responses = [
        AIMessage(content="", tool_calls=[
            {"name": "eval", "args": {"code": PROGRAM}, "id": "accounting", "type": "tool_call"},
        ]),
        AIMessage(content=json.dumps(store.answer(Query(), 1))),
    ]
    for response in responses:
        response.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    return store, responses


@pytest.mark.parametrize("case, expected_calls", [
    ("control", 2), ("malformed_final", 2), ("interpreter_error", 2), ("transfer_budget", 1),
])
def test_completed_usage_survives_validation_failures(scenario, case, expected_calls):
    store, responses = scenario
    if case == "malformed_final":
        responses[-1].content = "Here are the results: " + responses[-1].text
    elif case == "interpreter_error":
        responses[0].tool_calls[0]["args"]["code"] += "\nunknownVariable;"
    row = asyncio.run(run_probe(
        store, Query(), "bounded", model=RecipeModel(responses=responses),
        byte_budget=1 if case == "transfer_budget" else 8_000_000,
    ))
    # The same row is serialized by the notebook, including invalid attempts.
    saved = json.loads(json.dumps(row))
    assert saved["valid"] is (case == "control")
    if case == "transfer_budget":
        assert saved["error_type"] == "WorkBudgetExceeded", "Budget failure stops before a final model call."
    assert saved["model_calls"] == expected_calls
    assert saved["usage_complete"] is True
    assert (saved["input_tokens"], saved["output_tokens"], saved["total_tokens"]) == (
        100 * expected_calls, 20 * expected_calls, 120 * expected_calls,
    )
    assert [call["usage"]["total_tokens"] for call in saved["model_call_details"]] == [120] * expected_calls
    assert all(call["completed"] for call in saved["model_call_details"])


def test_missing_usage_retains_known_calls_without_inventing_a_total(scenario):
    store, responses = scenario
    responses[-1].usage_metadata = None
    row = asyncio.run(run_probe(store, Query(), "bounded", model=RecipeModel(responses=responses)))
    assert not row["valid"] and not row["usage_complete"]
    assert row["model_calls"] == 2
    assert all(row[name] is None for name in ("input_tokens", "output_tokens", "total_tokens"))
    assert [call["usage"] for call in row["model_call_details"]] == [
        {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}, None,
    ]


def test_provider_error_retains_prior_usage_and_failed_call(scenario):
    class FailingAfterToolModel(RecipeModel):
        async def _agenerate(self, *args, **kwargs):
            if self.i == 1:
                raise RuntimeError("Synthetic provider failure")
            return await super()._agenerate(*args, **kwargs)

    store, responses = scenario
    row = asyncio.run(run_probe(store, Query(), "bounded", model=FailingAfterToolModel(responses=responses)))
    assert not row["valid"] and row["error_type"] == "RuntimeError"
    assert not row["usage_complete"] and row["model_calls"] == 2
    assert all(row[name] is None for name in ("input_tokens", "output_tokens", "total_tokens"))
    first, failed = row["model_call_details"]
    assert first["completed"] and first["usage"]["total_tokens"] == 120
    assert not failed["completed"] and failed["usage"] is None
    assert failed["error_type"] == "RuntimeError"


@pytest.mark.parametrize("program", [PROGRAM, PROGRAM + "\nunknownVariable;"], ids=["valid", "invalid"])
def test_offline_probes_do_not_claim_model_usage(scenario, program):
    store, _ = scenario
    row = asyncio.run(run_probe(store, Query(), "bounded", program=program))
    assert row["valid"] is (program == PROGRAM)
    fields = ("model_calls", "usage_complete", "input_tokens", "output_tokens", "total_tokens")
    assert all(row[name] is None for name in fields)
    assert row["model_call_details"] == []
