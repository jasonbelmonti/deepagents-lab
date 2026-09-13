"""Audit one historical pilot extract and its tables; never invoke a model."""
import argparse
import hashlib
import json
from pathlib import Path

from deepagents_lab.experiments.graph_ptc_value.report import summarize

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/experiments/graph-ptc-value"
CORRECTED_SHA = "c1c0705ceb4d9f0e2233411a95294c87b30821d85e1cd801fe21ca620ed97900"
FIRST_SHA = "c102c9bd0b8202afd98bad196d06e419374acdf3d157eaa296f00fc1ebc81e0b"
TRIAL_FIELDS = (
    "case", "seed", "arm", "position", "evidence_kind", "correct", "valid",
    "usage_complete", "elapsed_seconds", "model_calls", "input_tokens",
    "output_tokens", "total_tokens", "validation", "response_bytes",
)


def project(raw_path):
    """Whitelist non-secret metrics from the exact immutable corrected report."""
    payload = Path(raw_path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != CORRECTED_SHA:
        raise ValueError("Raw report digest differs from the preserved corrected pilot.")
    raw = json.loads(payload)
    trials = []
    for row in raw["trials"]:
        selected = {key: row[key] for key in TRIAL_FIELDS}
        selected["model_call_details"] = [
            {"usage": {key: call["usage"][key] for key in
                       ("input_tokens", "output_tokens", "total_tokens")},
             "completed": call["completed"], "tool_names": call["tool_names"],
             "tool_result_text_chars": call["tool_result_text_chars"]}
            for call in row["model_call_details"]
        ]
        reads = [{key: call[key] for key in
                  ("name", "ids", "options", "ok", "response_bytes", "records")}
                 for call in row["application_tool_calls"]]
        # These batch reads are order-insensitive; retain duplicates and options.
        for call in reads:
            call["ids"] = sorted(call["ids"])
        canonical_reads = sorted(json.dumps(call, sort_keys=True) for call in reads)
        selected["backend_read_sha256"] = hashlib.sha256(
            json.dumps(canonical_reads).encode()).hexdigest()
        selected["backend_calls"] = len(reads)
        selected["eval_errors"] = sum(c["status"] == "error" for c in row["eval_calls"])
        trials.append(selected)
    return {
        "schema_version": 1, "sample_kind": "historical-development",
        "corrected_raw_sha256": CORRECTED_SHA, "excluded_first_raw_sha256": FIRST_SHA,
        "historical_primary": ["compute", "ptc"],
        "presentation_primary": ["ordinary", "ptc"],
        "presentation_secondary": ["compute", "ptc"],
        "correctness_basis": "Recorded historical scorer; not rescored on current code.",
        **{key: raw[key] for key in ("created_at", "config", "model_settings", "versions", "source_sha256")},
        "trials": trials,
    }


def number(value):
    return "—" if value is None else f"{value:,.1f}"


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |",
            "|" + "|".join("---" for _ in headers) + "|",
            *["| " + " | ".join(map(str, row)) + " |" for row in rows]]


def render_tables(data):
    """Recompute tables; keep all attempts separate from conditional pairs."""
    trials = data["trials"]
    summary = summarize(trials)
    lines = ["# Historical pilot: reproducible supporting tables", "",
             "Recorded historical correctness, not current-head validation. "
             "Primary: ordinary → PTC. Secondary: compute → PTC.", "",
             "Positive reduction favors PTC; negative favors the baseline. "
             "Median of per-seed percentages, not a ratio of pooled totals. "
             "A dash means no eligible pair. Cases are never pooled.", "",
             "## Every attempt", ""]
    lines += table(["Case", "Seed", "Arm", "Correct", "Calls", "Input tokens", "Output tokens", "Total tokens", "Seconds"], [
        [r["case"], r["seed"], r["arm"], r["correct"], r["model_calls"],
         r["input_tokens"], r["output_tokens"], r["total_tokens"], f'{r["elapsed_seconds"]:.3f}']
        for r in trials])
    lines += ["", "## All-attempt costs, including wrong answers", ""]
    lines += table(["Case", "Arm", "Correct / attempts", "Complete usage", "Total tokens", "Tokens / correct"], [
        [r["case"], r["arm"], f'{r["correct"]}/{r["attempts"]}', r["complete_usage"],
         r["total_tokens"], number(r["tokens_per_correct"])] for r in summary["groups"]])
    lines += ["", "## Matched efficiency, conditional on both arms passing", ""]
    lines += table(["Case", "Role", "Baseline → PTC", "Pairs", "Latency reduction %", "Calls reduction %", "Input reduction %", "Output reduction %", "Total reduction %"], [
        [r["case"], r["comparison_role"], r["baseline"] + " → PTC", r["matched_pairs"],
         *[number(r[k + "_reduction_pct"]) for k in
           ("elapsed_seconds", "model_calls", "input_tokens", "output_tokens", "total_tokens")]]
        for r in summary["comparisons"]])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-raw", type=Path, help="Verify the extract against the preserved raw report.")
    parser.add_argument("--tables", action="store_true", help="Print recomputed tables instead of checking the committed copy.")
    args = parser.parse_args()
    data = json.loads((EVIDENCE / "pilot-metrics.json").read_text())
    if args.verify_raw and project(args.verify_raw) != data:
        raise ValueError("Committed metrics differ from the whitelisted raw projection.")
    rendered = render_tables(data)
    if args.tables:
        print(rendered, end="")
    else:
        if rendered != (EVIDENCE / "pilot-tables.md").read_text():
            raise ValueError("Published tables differ from recomputed metrics.")
        print("Historical tables verified." + (" Raw projection verified." if args.verify_raw else ""))


if __name__ == "__main__":
    main()
