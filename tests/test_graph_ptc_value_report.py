import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from deepagents_lab.experiments.graph_ptc_value.config import CASES, Config, arm_order
from deepagents_lab.experiments.graph_ptc_value.report import render_report, summarize
from deepagents_lab.experiments.graph_ptc_value.runner import manifest, run_benchmark


def row(arm="ordinary", seed=1, tokens=100, seconds=10, correct=True, complete=True):
    return dict(case="depth-3", seed=seed, arm=arm, evidence_kind="live", correct=correct,
                usage_complete=complete, valid=correct and complete, elapsed_seconds=seconds,
                model_calls=4, input_tokens=tokens - 10 if complete else None,
                output_tokens=10 if complete else None, total_tokens=tokens if complete else None,
                model_call_details=[{"usage": {"total_tokens": tokens}}])


def test_matched_arithmetic_and_all_attempt_costs_include_failures():
    trials = [row(), row("ptc", tokens=50, seconds=5), row(seed=2, tokens=200),
              row("ptc", seed=2, tokens=300, correct=False)]
    summary = summarize(trials)
    comparison = next(r for r in summary["comparisons"] if r["baseline"] == "ordinary")
    assert comparison["matched_pairs"] == 1
    assert comparison["total_tokens_reduction_pct"] == comparison["elapsed_seconds_reduction_pct"] == 50
    ptc = next(r for r in summary["groups"] if r["arm"] == "ptc")
    assert ptc["correct"] == 1 and ptc["attempts"] == 2
    assert ptc["total_tokens"] == ptc["tokens_per_correct"] == 350
    assert "350.0" in render_report({"trials": trials})


def test_no_live_data_cannot_produce_a_benefit_claim():
    scripted = row()
    scripted["evidence_kind"] = "scripted"
    assert summarize([scripted])["groups"] == []
    for trials in ([], [scripted]):
        report = render_report({"trials": trials})
        assert "NOT MEASURED" in report
        assert "## Matched efficiency" not in report


def test_missing_usage_keeps_known_lower_bound_and_ptc_loss_is_visible():
    trials = [row(), row("ptc", tokens=200, seconds=20)]
    comparison = next(r for r in summarize(trials)["comparisons"] if r["baseline"] == "ordinary")
    assert comparison["total_tokens_reduction_pct"] == -100
    trials.append(row("ptc", seed=2, tokens=60, complete=False))
    ptc = next(r for r in summarize(trials)["groups"] if r["arm"] == "ptc")
    assert ptc["correct"] == 2 and ptc["total_tokens"] is None
    assert ptc["known_tokens_lower_bound"] == 260 and ptc["tokens_per_correct"] is None
    assert "-100.0" in render_report({"trials": trials})


def test_no_cross_case_matching_or_duplicate_seed_cherry_picking():
    trials = [row(), row("ptc")]
    trials[1]["case"] = "lookup"
    assert all(r["matched_pairs"] == 0 for r in summarize(trials)["comparisons"])
    trials[1]["case"] = "depth-3"
    trials.append(deepcopy(trials[1]))
    assert all(r["matched_pairs"] == 0 for r in summarize(trials)["comparisons"])


def test_primary_and_secondary_comparisons_are_explicit_and_keep_distinct_results():
    trials = [row(tokens=100), row("compute", tokens=200), row("ptc", tokens=50)]
    before = deepcopy(trials)
    comparisons = summarize(trials)["comparisons"]
    assert [(r["baseline"], r["comparison_role"]) for r in comparisons] == [
        ("ordinary", "primary"), ("compute", "secondary")]
    assert [r["total_tokens_reduction_pct"] for r in comparisons] == [50, 75]
    text = render_report({"trials": trials})
    assert "Primary comparison: **no interpreter (ordinary) vs interpreter with PTC**" in text
    assert "Secondary control: **compute-only interpreter vs PTC**" in text
    assert "primary | ordinary → PTC" in text and "secondary | compute → PTC" in text
    assert trials == before  # Rendering cannot relabel historical raw attempts.


def test_schedule_persists_each_trial_and_provenance(tmp_path, monkeypatch):
    from deepagents_lab.experiments.graph_ptc_value import runner

    seen = []
    config = replace(Config(), cases=(CASES[2],), seeds=(1, 2, 3))

    async def fake_trial(config, case, seed, arm, **kwargs):
        saved = json.loads(next(tmp_path.glob("*/report.json")).read_text())
        assert len(saved["trials"]) == len(seen)
        assert saved["pending_trial"]["arm"] == arm
        seen.append((seed, arm))
        return row(arm, seed)

    monkeypatch.setattr(runner, "run_trial", fake_trial)
    report = asyncio.run(run_benchmark(config, tmp_path, progress=lambda _: None))
    assert seen == [(seed, arm) for i, seed in enumerate(config.seeds) for arm in arm_order(i)]
    saved = json.loads(Path(report["report_path"]).read_text())
    assert "pending_trial" not in saved and len(saved["trials"]) == config.planned_runs
    assert saved["schema_version"] == 2
    assert saved["comparisons"] == {"primary": ["ordinary", "ptc"], "secondary": ["compute", "ptc"]}
    assert saved["source_sha256"]["trial.py"] and saved["source_sha256"]["incident_metrics.py"]
    assert len(saved["blocks"]) == 3
    assert set(saved["blocks"][0]["prompts"]) == {"ordinary", "compute", "ptc"}
    assert saved["blocks"][0]["fixture"] and saved["blocks"][0]["expected"]
    assert "GATHER_JS" not in str(saved["blocks"][0]["prompts"])


@pytest.mark.parametrize("interrupted", [False, True])
def test_early_stop_is_saved_with_failed_attempts(tmp_path, monkeypatch, interrupted):
    from deepagents_lab.experiments.graph_ptc_value import runner

    async def failure(config, case, seed, arm, **kwargs):
        return {**row(arm, seed, correct=False, complete=False), "error_status": 401,
                "interrupted": interrupted}

    monkeypatch.setattr(runner, "run_trial", failure)
    report = asyncio.run(run_benchmark(Config(), tmp_path, progress=lambda _: None))
    assert len(report["trials"]) == (1 if interrupted else 2)
    assert report["stop_reason"] and not report.get("pending_trial")
    assert json.loads(Path(report["report_path"]).read_text())["stop_reason"] == report["stop_reason"]


def test_offline_factory_cannot_fall_back_to_provider(tmp_path):
    with pytest.raises(ValueError, match="refusing a provider fallback"):
        asyncio.run(run_benchmark(Config(), tmp_path, model_factory=lambda *args: None, progress=lambda _: None))
    saved = json.loads(next(tmp_path.glob("*/report.json")).read_text())
    assert saved["pending_trial"] and saved["trials"] == []
    assert "unfinished trial" in render_report(saved)


def test_fixture_and_prompt_provenance_change_with_inputs():
    config = replace(Config(), seeds=(1,), cases=(CASES[2],))
    first = manifest(config)
    second = manifest(replace(config, seeds=(2,)))
    assert first["blocks"][0]["fixture_sha256"] != second["blocks"][0]["fixture_sha256"]
    assert first["blocks"][0]["prompts"] != second["blocks"][0]["prompts"]


def test_real_scripted_campaign_persists_without_provider_fallback(tmp_path, monkeypatch):
    from deepagents_lab.experiments.graph_ptc_value import trial
    from deepagents_lab.experiments.graph_ptc_value.smoke import scripted_model

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("Offline campaign attempted to initialize a provider.")

    monkeypatch.setattr(trial, "init_chat_model", forbidden_provider)
    config = replace(Config(), cases=(CASES[0], CASES[2]), seeds=(7,))
    result = asyncio.run(run_benchmark(config, tmp_path, model_factory=scripted_model, progress=lambda _: None))
    saved = json.loads(Path(result["report_path"]).read_text())
    assert saved == json.loads(json.dumps(result))  # JSON represents tuples as arrays.
    assert len(saved["trials"]) == saved["planned_runs"] == 6
    assert all(r["correct"] and r["backend_accounting_complete"] for r in saved["trials"])
    assert all(r["evidence_kind"] == "scripted" and not r["valid"] for r in saved["trials"])
    assert all(r["total_tokens"] is None for r in saved["trials"])
    assert saved["summary"]["live_attempts"] == 0 and saved["summary"]["comparisons"] == []
    assert "NOT MEASURED" in Path(result["report_path"]).with_suffix(".md").read_text()
