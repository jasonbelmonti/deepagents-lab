"""The published fresh campaign retains failures and reproducible arithmetic."""
import json
import runpy
import subprocess
import sys
from pathlib import Path
from statistics import median

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = runpy.run_path(str(ROOT / "scripts/check_graph_fresh.py"))
EVIDENCE = ROOT / "docs/experiments/graph-ptc-value/fresh-20260913"
DATA = json.loads((EVIDENCE / "metrics.json").read_text())


def test_complete_grid_failures_and_per_request_usage():
    rows = DATA["trials"]
    assert len(rows) == 60
    assert {(r["case"], r["seed"], r["arm"]) for r in rows} == {
        (case, seed, arm)
        for case in ("lookup", "depth-2", "depth-3", "width-12", "security-two-connectors")
        for seed in (39047, 58271, 76493, 91807)
        for arm in ("ordinary", "compute", "ptc")}
    assert sum(r["correct"] for r in rows) == 37
    assert sum(r["model_calls"] for r in rows) == 232
    assert [sum(r[k] for r in rows) for k in
            ("input_tokens", "output_tokens", "total_tokens")] == [1001618, 117249, 1118867]
    for row in rows:
        assert row["usage_complete"] and row["evidence_kind"] == "live"
        assert row["valid"] == row["correct"]
        assert len(row["model_call_details"]) == row["model_calls"]
        assert all(c["completed"] for c in row["model_call_details"])
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            assert sum(c["usage"][key] for c in row["model_call_details"]) == row[key]
        assert row["total_tokens"] == row["input_tokens"] + row["output_tokens"]
    errors = [r for r in rows if r["error_type"]]
    assert [(r["case"], r["seed"], r["arm"], r["error_type"]) for r in errors] == [
        ("lookup", 58271, "ptc", "ValueError")]
    assert errors[0]["validation"] is None and errors[0]["total_tokens"] == 3417
    assert sum(r["validation"] is not None and not r["validation"]["answer_correct"]
               for r in rows) == 22


@pytest.mark.parametrize("case,counts,pairs,tokens,latency", [
    ("lookup", (4, 4, 3), 3, -30.9, -58.8),
    ("depth-2", (4, 3, 4), 4, 36.5, 0.1),
    ("depth-3", (1, 2, 4), 1, 47.8, 24.1),
    ("width-12", (0, 0, 3), 0, None, None),
    ("security-two-connectors", (1, 1, 3), 0, None, None),
])
def test_primary_comparison_and_correctness(case, counts, pairs, tokens, latency):
    rows = [r for r in DATA["trials"] if r["case"] == case]
    assert tuple(sum(r["correct"] for r in rows if r["arm"] == arm)
                 for arm in ("ordinary", "compute", "ptc")) == counts
    matched = []
    for seed in DATA["config"]["seeds"]:
        pair = {r["arm"]: r for r in rows if r["seed"] == seed}
        if pair["ordinary"]["valid"] and pair["ptc"]["valid"]:
            matched.append(pair)
    assert len(matched) == pairs
    for metric, expected in (("total_tokens", tokens), ("elapsed_seconds", latency)):
        measured = median(100 * (p["ordinary"][metric] - p["ptc"][metric]) /
                          p["ordinary"][metric] for p in matched) if matched else None
        assert (round(measured, 1) if measured is not None else None) == expected


def test_frozen_config_and_publication_cli():
    frozen = json.loads((EVIDENCE / "frozen-config.json").read_text())
    assert DATA["config"] == frozen["config"]
    assert DATA["measured_head"] == frozen["head"] == AUDIT["MEASURED_HEAD"]
    assert DATA["comparisons"] == {"primary": ["ordinary", "ptc"], "secondary": ["compute", "ptc"]}
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_graph_fresh.py")],
                            cwd=ROOT.parent, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "tables and frozen configuration verified" in result.stdout


@pytest.mark.parametrize("case,pairs,tokens,latency", [
    ("lookup", 3, -12.4, -13.1), ("depth-2", 3, 41.4, -6.7),
    ("depth-3", 2, 34.5, 7.1), ("width-12", 0, None, None),
    ("security-two-connectors", 1, 56.0, 20.1),
])
def test_secondary_comparison_and_all_attempt_costs(case, pairs, tokens, latency):
    rows = [r for r in DATA["trials"] if r["case"] == case]
    paired = []
    for seed in DATA["config"]["seeds"]:
        p = {r["arm"]: r for r in rows if r["seed"] == seed}
        if p["compute"]["valid"] and p["ptc"]["valid"]:
            paired.append(p)
    assert len(paired) == pairs
    for metric, expected in (("total_tokens", tokens), ("elapsed_seconds", latency)):
        value = median(100 * (p["compute"][metric] - p["ptc"][metric]) /
                       p["compute"][metric] for p in paired) if paired else None
        assert (round(value, 1) if value is not None else None) == expected
    expected_totals = {
        "lookup": (19534, 31039, 23119), "depth-2": (56790, 67634, 36285),
        "depth-3": (102630, 108316, 56693), "width-12": (123177, 141318, 64615),
        "security-two-connectors": (92725, 129128, 65864),
    }
    groups = AUDIT["summarize"](rows)["groups"]
    for arm, expected in zip(("ordinary", "compute", "ptc"), expected_totals[case]):
        group = next(g for g in groups if g["arm"] == arm)
        assert group["total_tokens"] == expected
        correct = sum(r["correct"] for r in rows if r["arm"] == arm)
        assert group["tokens_per_correct"] == (expected / correct if correct else None)


@pytest.mark.parametrize("filename", ["metrics.json", "tables.md", "frozen-config.json"])
def test_altered_published_artifacts_fail_audit(tmp_path, filename):
    for name in ("metrics.json", "tables.md", "frozen-config.json"):
        (tmp_path / name).write_bytes((EVIDENCE / name).read_bytes())
    path = tmp_path / filename
    if filename == "metrics.json":
        data = json.loads(path.read_text())
        data["trials"][0]["total_tokens"] += 1
        path.write_text(json.dumps(data))
    else:
        path.write_text(path.read_text() + "\nchanged\n")
    with pytest.raises(ValueError):
        AUDIT["audit"](tmp_path)


def test_wrong_raw_source_rejected_without_exposure(tmp_path):
    raw = tmp_path / "report.json"
    raw.write_text('{"secret":"never-print-me"}')
    with pytest.raises(ValueError, match="digest") as error:
        AUDIT["project"](raw)
    assert "never-print-me" not in str(error.value)


def test_whitelist_excludes_raw_content():
    assert set(DATA) == {
        "schema_version", "sample_kind", "measured_head", "raw_sha256",
        "frozen_config_sha256", "created_at", "config", "comparisons",
        "model_settings", "versions", "source_sha256", "trials"}
    assert DATA["sample_kind"] == "fresh-seed-campaign"
    for row in DATA["trials"]:
        assert set(row) == set(AUDIT["TRIAL_FIELDS"]) | {"validation", "error_type", "model_call_details"}
        for call in row["model_call_details"]:
            assert set(call) == {"completed", "usage"}
            assert set(call["usage"]) == {"input_tokens", "output_tokens", "total_tokens"}
    text = (EVIDENCE / "metrics.json").read_text()
    for excluded in ('"run_id"', '"final_text"', '"tool_requests"', '"prompts"', "/Users/", "sk-proj-"):
        assert excluded not in text
