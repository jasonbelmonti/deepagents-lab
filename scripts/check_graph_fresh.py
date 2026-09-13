"""Read-only audit of the fixed 2026-09-13 campaign; never call a model."""
import argparse
import hashlib
import json
from pathlib import Path

from deepagents_lab.experiments.graph_ptc_value.report import summarize

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/experiments/graph-ptc-value/fresh-20260913"
RAW_SHA = "7b84342ae0f2bb99cb35c1314080e586fe2b1516ea40aafdc61240162b1c164e"
FROZEN_SHA = "1c4c4046e138e6d26777d1f63aa026ea2113247ce472f975ceb0e993c6292bf0"
METRICS_SHA = "f96b1911c4799e117ed1c1e8ad8204e05004149392bc4a67cfe5e770e889be80"
MEASURED_HEAD = "cb919679e221b39541d928358830f9b39f8d5124"
TRIAL_FIELDS = (
    "case", "seed", "arm", "position", "evidence_kind", "correct", "valid",
    "usage_complete", "elapsed_seconds", "model_calls", "input_tokens",
    "output_tokens", "total_tokens",
)


def project(raw_path):
    payload = Path(raw_path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != RAW_SHA:
        raise ValueError("Raw report digest does not match the preserved campaign.")
    raw = json.loads(payload)
    trials = []
    for row in raw["trials"]:
        selected = {key: row[key] for key in TRIAL_FIELDS}
        selected["validation"] = row.get("validation")
        selected["error_type"] = row.get("error_type")
        selected["model_call_details"] = [
            {"usage": {key: call["usage"][key] for key in
                       ("input_tokens", "output_tokens", "total_tokens")},
             "completed": call["completed"]}
            for call in row["model_call_details"]
        ]
        trials.append(selected)
    return {
        "schema_version": 1, "sample_kind": "fresh-seed-campaign",
        "measured_head": MEASURED_HEAD, "raw_sha256": RAW_SHA,
        "frozen_config_sha256": FROZEN_SHA,
        **{key: raw[key] for key in ("created_at", "config", "comparisons",
                                    "model_settings", "versions", "source_sha256")},
        "trials": trials,
    }


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(map(str, row)) + " |" for row in rows]]


def number(value):
    return "—" if value is None else f"{value:,.2f}"


def render_tables(data):
    summary = summarize(data["trials"])
    lines = ["# Fresh campaign: reproducible tables", "",
             "Measured main: " + MEASURED_HEAD + ". No historical pilot rows are included.", "",
             "Correct means the complete task, including exact JSON, ranking and supporting paths. "
             "All failures remain charged. Positive reductions favor PTC; "
             "a dash means undefined or no eligible pair.", "", "## Every attempt", ""]
    lines += table(["Case", "Seed", "Arm", "Correct", "Error / failed checks", "Calls",
                    "Input tokens", "Output tokens", "Total tokens", "Seconds"], [
        [r["case"], r["seed"], r["arm"], r["correct"],
         r["error_type"] or ", ".join(k for k, v in (r["validation"] or {}).items() if not v) or "—",
         r["model_calls"], r["input_tokens"], r["output_tokens"], r["total_tokens"],
         f'{r["elapsed_seconds"]:.3f}'] for r in data["trials"]])
    lines += ["", "## All-attempt costs", ""]
    lines += table(["Case", "Arm", "Correct / attempts", "Complete usage", "Total tokens", "Tokens / correct"], [
        [r["case"], r["arm"], f'{r["correct"]}/{r["attempts"]}', r["complete_usage"],
         r["total_tokens"], number(r["tokens_per_correct"])] for r in summary["groups"]])
    lines += ["", "## Matched efficiency", "",
              "Median per-seed percent reductions, conditional on both arms passing. Cases are never pooled.", ""]
    lines += table(["Case", "Role", "Baseline → PTC", "Pairs", "Latency reduction %",
                    "Calls reduction %", "Input reduction %", "Output reduction %", "Total reduction %"], [
        [r["case"], r["comparison_role"], r["baseline"] + " → PTC", r["matched_pairs"],
         *[number(r[k + "_reduction_pct"]) for k in
           ("elapsed_seconds", "model_calls", "input_tokens", "output_tokens", "total_tokens")]]
        for r in summary["comparisons"]])
    return "\n".join(lines) + "\n"


def audit(evidence=EVIDENCE, raw_path=None):
    frozen_payload = (evidence / "frozen-config.json").read_bytes()
    if hashlib.sha256(frozen_payload).hexdigest() != FROZEN_SHA:
        raise ValueError("Frozen configuration digest differs.")
    payload = (evidence / "metrics.json").read_bytes()
    if hashlib.sha256(payload).hexdigest() != METRICS_SHA:
        raise ValueError("Metrics digest differs from the preserved publication.")
    data = json.loads(payload)
    if raw_path and project(raw_path) != data:
        raise ValueError("Metrics differ from the exact raw projection.")
    if data["config"] != json.loads(frozen_payload)["config"]:
        raise ValueError("Metrics differ from the frozen configuration.")
    if render_tables(data) != (evidence / "tables.md").read_text():
        raise ValueError("Tables differ from recomputed metrics.")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-raw", type=Path)
    args = parser.parse_args()
    audit(raw_path=args.verify_raw)
    print("Fresh campaign tables and frozen configuration verified." +
          (" Raw projection verified." if args.verify_raw else ""))


if __name__ == "__main__":
    main()
