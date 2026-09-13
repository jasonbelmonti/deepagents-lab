"""Failure-aware accounting and matched descriptive comparisons, not a win gate."""
from statistics import median

from .config import ARMS


def summarize(trials):
    live = [row for row in trials if row["evidence_kind"] == "live"]
    groups, comparisons = [], []
    for case in sorted({row["case"] for row in live}):
        rows = [row for row in live if row["case"] == case]
        for arm in ARMS:
            arm_rows = [row for row in rows if row["arm"] == arm]
            if not arm_rows:
                continue
            correct = sum(row["correct"] for row in arm_rows)
            complete = all(row["usage_complete"] for row in arm_rows)
            total = sum(row["total_tokens"] for row in arm_rows) if complete else None
            known = sum(call["usage"]["total_tokens"] for row in arm_rows
                        for call in row["model_call_details"] if call.get("usage") is not None)
            groups.append(dict(case=case, arm=arm, attempts=len(arm_rows), correct=correct,
                               complete_usage=sum(row["usage_complete"] for row in arm_rows),
                               total_tokens=total, known_tokens_lower_bound=known,
                               tokens_per_correct=total / correct if total is not None and correct else None))
        for baseline in ("ordinary", "compute"):
            pairs = []
            for seed in sorted({row["seed"] for row in rows}):
                matches = [row for row in rows if row["seed"] == seed and row["arm"] in (baseline, "ptc")]
                if len(matches) != 2 or {r["arm"] for r in matches} != {baseline, "ptc"}:
                    continue
                if all(r["valid"] and r["correct"] and r["usage_complete"] for r in matches):
                    pairs.append({r["arm"]: r for r in matches})
            item = dict(case=case, baseline=baseline, matched_pairs=len(pairs),
                        comparison_role="primary" if baseline == "ordinary" else "secondary")
            for metric in ("elapsed_seconds", "model_calls", "input_tokens", "output_tokens", "total_tokens"):
                reductions = [100 * (p[baseline][metric] - p["ptc"][metric]) / p[baseline][metric]
                              for p in pairs if p[baseline][metric] > 0]
                item[metric + "_reduction_pct"] = median(reductions) if reductions else None
            comparisons.append(item)
    return {"live_attempts": len(live), "scripted_attempts": len(trials) - len(live),
            "groups": groups, "comparisons": comparisons}


def number(value):
    return "unknown" if value is None else f"{value:,.1f}"


def render_report(report):
    summary = summarize(report["trials"])
    lines = ["# Graph PTC value: descriptive pilot", "",
             "Primary comparison: **no interpreter (ordinary) vs interpreter with PTC**.",
             "Secondary control: **compute-only interpreter vs PTC**, to examine the tool bridge separately.", ""]
    if not summary["live_attempts"]:
        lines += ["**NOT MEASURED: no real-model evidence.** Scripted runs verify plumbing only; they cannot establish latency or token benefits.", ""]
    else:
        lines += ["No automatic hypothesis acceptance. Positive reductions favor PTC; negative reductions favor the baseline.",
                  "Check correctness and all-attempt costs before interpreting matched efficiency. Small samples are exploratory, not production estimates.", ""]
    lines += ["## Every attempt", "", "| Case | Seed | Arm | Evidence | Correct | Usage complete | Seconds | Model calls | Input tokens | Output tokens |",
              "|---|---:|---|---|---|---|---:|---:|---:|---:|"]
    for row in report["trials"]:
        lines.append(f"| {row['case']} | {row['seed']} | {row['arm']} | {row['evidence_kind']} | {row['correct']} | "
                     f"{row['usage_complete']} | {number(row.get('elapsed_seconds'))} | {row['model_calls']} | "
                     f"{number(row['input_tokens'])} | {number(row['output_tokens'])} |")
    if summary["live_attempts"]:
        lines += ["", "## All-attempt costs (including failures)", "",
                  "| Case | Arm | Correct / attempts | Complete usage | Total tokens | Known lower bound | Tokens / correct answer |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for row in summary["groups"]:
            lines.append(f"| {row['case']} | {row['arm']} | {row['correct']}/{row['attempts']} | {row['complete_usage']} | "
                         f"{number(row['total_tokens'])} | {number(row['known_tokens_lower_bound'])} | {number(row['tokens_per_correct'])} |")
        lines += ["", "## Matched efficiency, conditional on both arms passing", "",
                  "Median per-pair percent reduction; cases are never pooled. Unknown means no eligible comparison (or zero denominator).", "",
                  "| Case | Role | Baseline → PTC | Pairs | Latency reduction % | Model-call reduction % | Input-token reduction % | Output-token reduction % | Total-token reduction % |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|"]
        for row in summary["comparisons"]:
            values = " | ".join(number(row[key + "_reduction_pct"]) for key in (
                "elapsed_seconds", "model_calls", "input_tokens", "output_tokens", "total_tokens"))
            lines.append(f"| {row['case']} | {row['comparison_role']} | {row['baseline']} → PTC | {row['matched_pairs']} | {values} |")
    lines += ["", "Raw JSON includes every observed model call, generated tool/code requests, backend reads and partial usage.",
              "Cached/reasoning tokens are subsets, not extra totals. Backend service durations may overlap; do not add them to wall time.",
              "Aborted trials retain a frozen backend snapshot and observed lower bounds; unfinished work may complete later, so backend totals remain unknown.",
              "Tool payload bytes and input text characters are diagnostics, not token counts. Initialization and oracle time are excluded from invocation latency."]
    if report.get("pending_trial"):
        lines += ["", "An unfinished trial is recorded. This campaign is incomplete; do not present it as a complete comparison."]
    if report.get("stop_reason"):
        lines += ["", "Stopped: " + report["stop_reason"]]
    return "\n".join(lines) + "\n"
