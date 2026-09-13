import asyncio
import json
from dataclasses import replace
from xml.etree import ElementTree

import pytest
from langchain_core.messages import AIMessage
from langsmith import tracing_context

from deepagents_lab.experiments.graph_ptc_value.config import ARMS, CASES, Config, Scenario, VARIANT
from deepagents_lab.experiments.graph_ptc_value.fixture import make_graph
from deepagents_lab.experiments.graph_ptc_value.oracle import expected_answer
from deepagents_lab.experiments.graph_ptc_value.smoke import ScriptedModel, message, scripted_model
from deepagents_lab.experiments.graph_ptc_value.trial import run_trial


@pytest.fixture(autouse=True)
def no_external_traces():
    with tracing_context(enabled=False):
        yield


@pytest.mark.parametrize("case", [CASES[0], CASES[1], CASES[2], CASES[3], VARIANT])
@pytest.mark.parametrize("arm", ARMS)
def test_actual_graph_and_interpreter_results_agree_without_fake_usage(case, arm):
    pytest.importorskip("langchain_quickjs")
    config = Config()
    row = asyncio.run(run_trial(config, case, 1103, arm, model=scripted_model(config, case, 1103, arm)))
    assert row["correct"], row
    assert row["evidence_kind"] == "scripted" and not row["valid"]
    assert row["total_tokens"] is None and not row["usage_complete"]
    assert row["backend_accounting_complete"]
    assert all(call["ok"] for call in row["application_tool_calls"])
    assert all(call["delivered"] for call in row["application_tool_calls"])
    assert row["response_bytes"] == row["response_bytes_lower_bound"]
    expected = expected_answer(make_graph(1103, case.width), case)
    if arm in ("compute", "ptc") and case.kind != "lookup":
        assert json.loads(ElementTree.fromstring(row["eval_calls"][-1]["output"]).text) == expected


@pytest.mark.parametrize("seed", [7, 42, 99])
def test_independent_javascript_solver_matches_oracle_on_unseen_graphs(seed):
    pytest.importorskip("langchain_quickjs")
    case, config = Scenario(depth=4, min_connectors=2), Config()
    row = asyncio.run(run_trial(config, case, seed, "ptc", model=scripted_model(config, case, seed, "ptc")))
    assert row["correct"], row


def test_compute_only_cannot_call_graph_tools_and_bad_results_are_rejected():
    pytest.importorskip("langchain_quickjs")
    case, config = CASES[0], Config()
    root = make_graph(7).root
    code = f"JSON.stringify(await tools.getProfiles({{person_ids:[{json.dumps(root)}],fields:['topic']}}))"
    expected = expected_answer(make_graph(7), case)
    # No actual graph reads: even a guessed correct final answer cannot pass.
    model = ScriptedModel(responses=[message([("eval", {"code": code})], 0), AIMessage(content=json.dumps(expected))])
    row = asyncio.run(run_trial(config, case, 7, "compute", model=model))
    assert not row["correct"] and not row["application_tool_calls"]
    assert ElementTree.fromstring(row["eval_calls"][0]["output"]).tag == "error"
    good = scripted_model(config, case, 7, "ptc")
    good.responses[-1] = AIMessage(content="[]")
    row = asyncio.run(run_trial(config, case, 7, "ptc", model=good))
    assert not row["correct"] and not row["validation"]["answer_correct"]


def test_parallel_batch_apis_identical_and_ptc_context_omits_raw_edges():
    pytest.importorskip("langchain_quickjs")
    case, config = Scenario(), Config()
    rows = [asyncio.run(run_trial(config, case, 7, arm, model=scripted_model(config, case, 7, arm))) for arm in ARMS]
    assert all(row["correct"] for row in rows)
    def reads(row):
        return sorted((c["name"], tuple(sorted(c["ids"])), c["response_bytes"]) for c in row["application_tool_calls"])
    assert reads(rows[0]) == reads(rows[1]) == reads(rows[2])
    assert rows[0]["model_calls"] > rows[2]["model_calls"]
    assert sum(r["tool_result_text_chars"] for r in rows[0]["model_call_details"]) > sum(
        r["tool_result_text_chars"] for r in rows[2]["model_call_details"])


def test_provider_failure_retains_known_usage_and_missing_totals(monkeypatch):
    pytest.importorskip("langchain_quickjs")
    from deepagents_lab.experiments.graph_ptc_value import trial

    class FailsSecond(ScriptedModel):
        def _generate(self, *args, **kwargs):
            if self.i:
                raise RuntimeError("synthetic provider failure")
            return super()._generate(*args, **kwargs)

    case, config = CASES[0], Config()
    reference = scripted_model(config, case, 7, "ordinary")
    reference.responses[0].usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    model = FailsSecond(responses=reference.responses)
    # Substitute the provider boundary locally; no network and no real result artifact.
    monkeypatch.setattr(trial, "init_chat_model", lambda *a, **k: model)
    row = asyncio.run(run_trial(config, case, 7, "ordinary"))
    assert row["error_type"] == "RuntimeError" and not row["correct"]
    assert row["model_calls"] == 2 and row["total_tokens"] is None
    assert row["model_call_details"][0]["usage"]["total_tokens"] == 120
    assert row["model_call_details"][1]["completed"] is False


def test_malformed_final_preserves_complete_usage(monkeypatch):
    from deepagents_lab.experiments.graph_ptc_value import trial

    config, case = Config(), CASES[0]
    model = scripted_model(config, case, 7, "ordinary")
    model.responses[-1] = AIMessage(content="Not JSON")
    for response in model.responses:
        response.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    monkeypatch.setattr(trial, "init_chat_model", lambda *a, **k: model)
    row = asyncio.run(run_trial(config, case, 7, "ordinary"))
    assert not row["correct"] and row["usage_complete"] and row["total_tokens"] == 240


def test_timeout_is_failure_not_an_empty_answer():
    class SlowModel(ScriptedModel):
        async def _agenerate(self, *args, **kwargs):
            await asyncio.sleep(1)
            return await super()._agenerate(*args, **kwargs)

    config, case = replace(Config(), run_timeout=0.05), CASES[0]
    model = SlowModel(responses=[AIMessage(content="[]")])
    row = asyncio.run(run_trial(config, case, 7, "ordinary", model=model))
    assert not row["correct"] and row["error_type"] == "TimeoutError"


def test_scripted_usage_numbers_are_removed():
    config, case = Config(), CASES[0]
    model = scripted_model(config, case, 7, "ordinary")
    for response in model.responses:
        response.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    row = asyncio.run(run_trial(config, case, 7, "ordinary", model=model))
    assert row["correct"] and row["total_tokens"] is None and not row["valid"]
    assert all(call["usage"] is None for call in row["model_call_details"])


def test_cancellation_retains_already_observed_provider_usage(monkeypatch):
    from deepagents_lab.experiments.graph_ptc_value import trial

    config, case = Config(), CASES[0]
    reference = scripted_model(config, case, 7, "ordinary")
    reference.responses[0].usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}

    async def cancel_in_flight():
        second_started = asyncio.Event()

        class BlockSecond(ScriptedModel):
            async def _agenerate(self, *args, **kwargs):
                if self.i:
                    second_started.set()
                    await asyncio.Event().wait()
                return await super()._agenerate(*args, **kwargs)

        model = BlockSecond(responses=reference.responses)
        monkeypatch.setattr(trial, "init_chat_model", lambda *a, **k: model)
        task = asyncio.create_task(run_trial(config, case, 7, "ordinary"))
        await asyncio.wait_for(second_started.wait(), timeout=5)
        task.cancel()  # Cancel the invocation, not just an internal model node.
        return await task

    row = asyncio.run(cancel_in_flight())
    assert row.get("interrupted") and not row["correct"] and row["total_tokens"] is None, row
    assert row["model_call_details"][0]["usage"]["total_tokens"] == 120
