"""Published historical evidence and notebook spend-boundary acceptance checks."""
import json
import runpy
from copy import deepcopy
from pathlib import Path
from statistics import median

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = runpy.run_path(str(ROOT / "scripts/check_graph_pilot.py"))
EVIDENCE = ROOT / "docs/experiments/graph-ptc-value"
DATA = json.loads((EVIDENCE / "pilot-metrics.json").read_text())


def test_complete_historical_sample_and_per_request_usage():
    rows = DATA["trials"]
    assert DATA["sample_kind"] == "historical-development"
    assert DATA["corrected_raw_sha256"] == AUDIT["CORRECTED_SHA"]
    assert DATA["excluded_first_raw_sha256"] == AUDIT["FIRST_SHA"]
    assert DATA["historical_primary"] == ["compute", "ptc"]
    assert DATA["presentation_primary"] == ["ordinary", "ptc"]
    assert len(rows) == 24
    assert {(r["case"], r["seed"], r["arm"]) for r in rows} == {
        (case, seed, arm) for case in ("lookup", "depth-2", "depth-3", "width-12")
        for seed in (1103, 2213) for arm in ("ordinary", "compute", "ptc")}
    assert sum(r["correct"] for r in rows) == 19
    assert sum(r["model_calls"] for r in rows) == 86
    assert sum(r["input_tokens"] for r in rows) == 359236
    assert sum(r["output_tokens"] for r in rows) == 45610
    assert sum(r["total_tokens"] for r in rows) == 404846
    for row in rows:
        assert row["evidence_kind"] == "live" and row["usage_complete"]
        assert row["correct"] == all(row["validation"].values()) == row["valid"]
        assert len(row["model_call_details"]) == row["model_calls"]
        assert all(c["completed"] for c in row["model_call_details"])
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            assert sum(c["usage"][key] for c in row["model_call_details"]) == row[key]
        assert row["total_tokens"] == row["input_tokens"] + row["output_tokens"]


@pytest.mark.parametrize("case,pairs,tokens,latency", [
    ("lookup", 2, -30.8, -24.9), ("depth-2", 2, 6.9, -17.9),
    ("depth-3", 1, 56.3, 17.7), ("width-12", 1, 52.6, 32.8),
])
def test_published_primary_numbers_recompute_without_pooling(case, pairs, tokens, latency):
    matched = []
    for seed in (1103, 2213):
        pair = {r["arm"]: r for r in DATA["trials"] if r["case"] == case and r["seed"] == seed}
        if pair["ordinary"]["valid"] and pair["ptc"]["valid"]:
            matched.append(pair)
    assert len(matched) == pairs
    for metric, expected in (("total_tokens", tokens), ("elapsed_seconds", latency)):
        observed = median(100 * (p["ordinary"][metric] - p["ptc"][metric]) /
                          p["ordinary"][metric] for p in matched)
        assert round(observed, 1) == expected


def test_failure_costs_and_secondary_mechanism_are_not_cherry_picked():
    rows = DATA["trials"]
    assert {(r["case"], r["seed"], r["arm"]) for r in rows if not r["correct"]} == {
        ("depth-3", 1103, "ordinary"), ("depth-3", 1103, "compute"),
        ("depth-3", 2213, "compute"), ("width-12", 2213, "ordinary"),
        ("width-12", 2213, "compute")}
    width = [r for r in rows if r["case"] == "width-12"]
    assert [sum(r["total_tokens"] for r in width if r["arm"] == arm) /
            sum(r["correct"] for r in width if r["arm"] == arm)
            for arm in ("ordinary", "compute", "ptc")] == [58725, 70623, 13539]
    pair = {r["arm"]: r for r in width if r["seed"] == 1103}
    compute, ptc = pair["compute"], pair["ptc"]
    assert compute["correct"] and ptc["correct"]
    assert compute["backend_read_sha256"] == ptc["backend_read_sha256"]
    assert compute["backend_calls"] == ptc["backend_calls"] == 5
    assert compute["response_bytes"] == ptc["response_bytes"] == 8720
    assert [sum(c["tool_result_text_chars"] for c in r["model_call_details"])
            for r in (compute, ptc)] == [35203, 2331]
    assert ptc["elapsed_seconds"] > compute["elapsed_seconds"]
    assert sum("eval" in c["tool_names"] for r in rows if r["arm"] == "compute"
               for c in r["model_call_details"]) == 1
    assert round(100 * (41092 - 13790) / 41092, 1) == 66.4
    assert round(100 * (37031 - 10147) / 37031, 1) == 72.6
    assert round(100 * (35203 - 2331) / 35203, 1) == 93.4


def test_published_tables_match_and_changed_measurements_change_tables():
    render = AUDIT["render_tables"]
    assert render(DATA) == (EVIDENCE / "pilot-tables.md").read_text()
    changed = deepcopy(DATA)
    changed["trials"][0]["elapsed_seconds"] *= 2
    assert render(changed) != render(DATA)
    narrative = (EVIDENCE / "pilot-findings.md").read_text()
    for caveat in ("post-hoc", "inconclusive", "historical scorer", "not dollars"):
        assert caveat in narrative
    assert "19" in narrative and "404,846" in narrative


def test_raw_verifier_rejects_wrong_source_without_exposing_it(tmp_path):
    source = tmp_path / "unrelated.json"
    source.write_text('{"secret": "do-not-publish"}')
    with pytest.raises(ValueError, match="digest differs") as error:
        AUDIT["project"](source)
    assert "do-not-publish" not in str(error.value)


def test_default_run_all_never_loads_env_or_initializes_a_provider():
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    notebook = nbformat.read(ROOT / "notebooks/experiments/graph-ptc-value.ipynb", as_version=4)
    notebook.cells.insert(0, nbformat.v4.new_code_cell("""
import os
os.environ["OPENAI_API_KEY"] = "offline-sentinel"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
import dotenv
from deepagents_lab.experiments.graph_ptc_value import trial
def forbidden(*args, **kwargs):
    raise AssertionError("Default Run All crossed the provider/.env boundary")
trial.init_chat_model = forbidden
dotenv.load_dotenv = forbidden
"""))
    notebook.cells.append(nbformat.v4.new_code_cell("""
assert RUN_LIVE is False and live_report is None
assert len(offline_report["trials"]) == 3
assert all(r["correct"] and r["total_tokens"] is None for r in offline_report["trials"])
assert historical_metrics["sample_kind"] == "historical-development"
"""))
    nbclient.NotebookClient(notebook, timeout=120, kernel_name="python3",
                            resources={"metadata": {"path": str(ROOT / "notebooks/experiments")}}).execute()
