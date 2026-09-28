"""Grouped holdout, validation-only tuning, and auditable family-retrieval metrics."""
from collections import Counter
from time import perf_counter

import numpy as np

from .predictor import CorrectionIndex

ARMS = ("direct_correction", "problem_neighbors", "ridge_prediction")


def split_records(records, seed=42):
    records = list(records)
    if len({r.event.event_id for r in records}) != len(records):
        raise ValueError("Duplicate event IDs would distort evaluation.")
    if len({r.embedding_id for r in records}) != 1:
        raise ValueError("All records must use one embedding backend and dimension.")
    groups = sorted({r.event.group_id for r in records})
    if len(groups) < 5:
        raise ValueError("Use at least five independent task/conversation groups.")
    np.random.default_rng(seed).shuffle(groups)
    n_val = n_test = max(1, len(groups) // 5)
    assignment = {
        **{g: "test" for g in groups[:n_test]},
        **{g: "validation" for g in groups[n_test:n_test + n_val]},
        **{g: "train" for g in groups[n_test + n_val:]},
    }
    return {name: [r for r in records if assignment[r.event.group_id] == name]
            for name in ("train", "validation", "test")}


def score_queries(index, queries, arm):
    started = perf_counter()
    scores = index.scores([r.x for r in queries], arm)
    elapsed_ms = (perf_counter() - started) * 1000
    rows = []
    for record, values in zip(queries, scores):
        order = np.argsort(-values, kind="stable")
        matches = [rank for rank, i in enumerate(order, 1) if index.records[i].event.family == record.event.family]
        best = index.records[order[0]]
        # Margin against the best DIFFERENT family, not a duplicate of the winner.
        other = [values[i] for i in order if index.records[i].event.family != best.event.family]
        rows.append({
            "event_id": record.event.event_id, "expected_family": record.event.family,
            "predicted_family": best.event.family, "candidate_id": best.event.event_id,
            "correction": best.pair.correction, "score": float(values[order[0]]),
            "margin": float(values[order[0]] - max(other)) if other else 0.0,
            "supported_family": bool(matches), "hit_at_1": bool(matches and matches[0] == 1),
            "hit_at_3": bool(matches and matches[0] <= 3), "reciprocal_rank": 1 / matches[0] if matches else 0.0,
        })
    return rows, elapsed_ms


def summarize(rows, arm, elapsed_ms):
    return {"arm": arm, "queries": len(rows),
            **{name: float(np.mean([row[name] for row in rows]))
               for name in ("hit_at_1", "hit_at_3", "reciprocal_rank", "supported_family")},
            "batch_predict_ms": elapsed_ms}


def evaluate(records, seed=42, alphas=(0.01, 0.1, 1.0, 10.0)):
    splits = split_records(records, seed)
    if not alphas:
        raise ValueError("Supply at least one regularization candidate.")
    tuning = []
    for alpha in alphas:
        candidate = CorrectionIndex(splits["train"], alpha)
        rows, elapsed = score_queries(candidate, splits["validation"], "ridge_prediction")
        tuning.append({"alpha": alpha, **summarize(rows, "ridge_prediction", elapsed)})
    chosen = max(tuning, key=lambda row: (row["reciprocal_rank"], row["alpha"]))["alpha"]
    index = CorrectionIndex(splits["train"], chosen)
    trials, summary = {}, []
    for arm in ARMS:
        rows, elapsed = score_queries(index, splits["test"], arm)
        trials[arm] = rows
        summary.append(summarize(rows, arm, elapsed))
    majority = Counter(r.event.family for r in splits["train"]).most_common(1)[0][0]
    report = {
        "seed": seed, "embedding_id": records[0].embedding_id,
        "synthetic": all(r.event.synthetic for r in records),
        "capture_origins": sorted({r.origin for r in records}),
        "split_event_ids": {key: [r.event.event_id for r in values] for key, values in splits.items()},
        "split_group_ids": {key: sorted({r.event.group_id for r in values}) for key, values in splits.items()},
        "tuning": tuning, "chosen_alpha": chosen, "summary": summary, "trials": trials,
        "majority_family_hit_at_1": float(np.mean([r.event.family == majority for r in splits["test"]])),
        "predictor_bytes": index.mapping.bytes,
        "interpretation": "Correction-family retrieval given a captured problem; no detection or repair efficacy claim.",
    }
    return report, index, splits


def margin_sweep(index, queries, thresholds=(0.0, 0.02, 0.05, 0.1, 0.2)):
    rows, _ = score_queries(index, queries, "ridge_prediction")
    results = []
    for threshold in thresholds:
        accepted = [r for r in rows if r["margin"] >= threshold]
        results.append({"threshold": threshold, "accepted": len(accepted), "coverage": len(accepted) / len(rows),
                        "family_precision": float(np.mean([r["hit_at_1"] for r in accepted])) if accepted else None})
    return results
