"""Paired summaries with visible failures and explicitly defined percentiles."""

from __future__ import annotations

from math import ceil
from statistics import median
from typing import Any


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile; with five trials, p95 is the observed maximum."""
    if not values or not 0 < fraction <= 1:
        raise ValueError("A percentile needs observations and a fraction in (0, 1].")
    return sorted(values)[ceil(len(values) * fraction) - 1]


def summarize(trials: list[dict[str, Any]]) -> dict[str, Any]:
    pairs: dict[int, list[dict[str, Any]]] = {}
    for row in trials:
        pairs.setdefault(row["pair"], []).append(row)
    valid_pairs = {
        pair for pair, rows in pairs.items()
        if len(rows) == 2 and {row["arm"] for row in rows} == {"ordinary", "ptc"}
        and all(row["valid"] for row in rows)
    }
    summary: dict[str, Any] = {
        "valid_pairs": len(valid_pairs),
        "invalid_trials": sum(not row["valid"] for row in trials),
        "trials_recorded": len(trials),
    }
    for arm in ("ordinary", "ptc"):
        rows = [row for row in trials if row["arm"] == arm and row["pair"] in valid_pairs]
        if not rows:
            continue
        summary[arm] = {
            "latency_p50_seconds": median(row["elapsed_seconds"] for row in rows),
            "latency_p95_seconds": percentile([row["elapsed_seconds"] for row in rows], 0.95),
            **{
                f"{field}_p50": median(row[field] for row in rows)
                for field in ("model_calls", "input_tokens", "output_tokens", "total_tokens")
            },
        }
    return summary


def render_report(report: dict[str, Any]) -> str:
    summary = summarize(report["trials"])
    config = report["config"]
    lines = [
        "# Four-stage incident triage: ordinary tools vs PTC",
        "",
        f"Model: `{config['model']}`. Records: {config['records']}. "
        f"Intermediate record size: {config['payload_bytes']} bytes. "
        f"Requested pairs: {config['pairs']}.",
        "",
        f"Valid complete pairs: **{summary['valid_pairs']}**. "
        f"Invalid trials: **{summary['invalid_trials']}**. "
        f"Trials recorded: {summary['trials_recorded']}/{2 * config['pairs']}.",
        "",
        "## Every trial",
        "",
        "| Pair | Order | Arm | Valid | Seconds | Model calls | Input | Output | Total | Cached input | Reasoning |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    failures = []
    for row in report["trials"]:
        values = [
            row["pair"], row["position"], row["arm"], row["valid"],
            f"{row['elapsed_seconds']:.3f}", row["model_calls"], row["input_tokens"],
            row["output_tokens"], row["total_tokens"], row["cache_read_tokens"], row["reasoning_tokens"],
        ]
        lines.append("| " + " | ".join("unknown" if value is None else str(value) for value in values) + " |")
        if not row["valid"]:
            failed = ", ".join(
                check for check in ("answer_correct", "coverage_correct", "path_correct", "usage_complete")
                if not row.get(check)
            )
            failures.append(f"Pair {row['pair']} {row['arm']}: failed {failed}; error type: {row.get('error_type', 'none')}.")
    if failures:
        lines.extend(["", *failures])
    if report.get("stop_reason"):
        lines.extend(["", report["stop_reason"]])
    lines.extend(["", "## Comparison: valid complete pairs only", ""])
    if summary["valid_pairs"]:
        lines.extend([
            "| Metric | Ordinary | PTC | Reduction |",
            "|---|---:|---:|---:|",
        ])
        for field, label in (
            ("latency_p50_seconds", "Latency p50 (seconds)"),
            ("latency_p95_seconds", "Latency p95 (seconds)"),
            ("model_calls_p50", "Model calls p50"),
            ("input_tokens_p50", "Input tokens p50"),
            ("output_tokens_p50", "Output tokens p50"),
            ("total_tokens_p50", "Total tokens p50"),
        ):
            ordinary, ptc = summary["ordinary"][field], summary["ptc"][field]
            delta = f"{100 * (ordinary - ptc) / ordinary:.1f}%" if ordinary else "n/a"
            lines.append(f"| {label} | {ordinary:.3f} | {ptc:.3f} | {delta} |")
    else:
        lines.append("No efficiency comparison available until a complete pair passes validation.")
    lines.extend([
        "",
        "Positive reductions mean lower PTC measurements; negative values mean PTC was higher. "
        "Both paths must process every record exactly once at all four stages and return the exact expected JSON.",
        "",
        "p50 is the median; p95 uses nearest rank. With five pairs, p95 is the maximum of five observations, "
        "an exploratory tail statistic. Five pairs do not establish a stable production p95 or statistical significance.",
        "",
        "Each trial gets a fresh agent, model client, fixture and thread. Order alternates by pair. "
        "The model writes the PTC program; no prewritten program is supplied. Latency spans ainvoke, "
        "including model and tool execution, but excludes graph construction. Tools are in-memory batch APIs "
        "with no artificial delay. Both arms receive the same 1–2 KB intermediate records; only PTC can "
        "keep them outside model context. This measures depth plus payload filtering together.",
        "",
        "Provider cache state is uncontrolled; cached input and reasoning tokens are reported separately "
        "when available and are already included in input/output totals. Tokens are usage, not dollar cost. "
        "SDK retries are disabled. Model-level tool retries remain measured. Every failed trial is retained; "
        "both members of an invalid pair are excluded from the comparison.",
        "",
        "Raw JSON includes model calls, validation, tool coverage, prompts, settings, dependency versions "
        "and source/fixture hashes. This synthetic experiment does not select the lab's evaluation framework.",
    ])
    return "\n".join(lines) + "\n"
