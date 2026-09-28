"""Validation-only tuning with an untouched test set and auditable predictions."""
from .gate import select_threshold
from .metrics import query_rows, summarize
from .policy import ARMS, StatePolicy
from .splits import split_records


def evaluate(records, seed=42, alphas=(0.01, 0.1, 1.0, 10.0), gate_alpha=1.0,
             max_validation_false_positive_rate=0.1):
    records = list(records)
    splits = split_records(records, seed)
    if not alphas:
        raise ValueError("Supply at least one regularization candidate.")
    tuning = []
    for alpha in alphas:
        candidate = StatePolicy.fit(splits["train"], alpha, gate_alpha)
        summary = summarize(query_rows(candidate, splits["validation"], "ridge_prediction"), "ridge_prediction")
        tuning.append({"alpha": alpha, "positive_mrr": summary["positive_mrr"]})
    chosen_alpha = max(tuning, key=lambda r: (r["positive_mrr"], r["alpha"]))["alpha"]
    policy = StatePolicy.fit(splits["train"], chosen_alpha, gate_alpha)
    selected, sweep = select_threshold(
        policy.gate.scores([r.s for r in splits["validation"]]),
        [r.example.needs_intervention for r in splits["validation"]], max_validation_false_positive_rate,
    )
    policy.threshold = selected["threshold"]
    trials = {arm: query_rows(policy, splits["test"], arm) for arm in ("no_intervention", *ARMS)}
    report = {
        "seed": seed, "embedding_id": policy.embedding_id, "state_format": policy.state_format,
        "synthetic": all(r.example.synthetic for r in records),
        "split_sample_ids": {name: [r.example.sample_id for r in rows] for name, rows in splits.items()},
        "split_group_ids": {name: sorted({r.example.group_id for r in rows}) for name, rows in splits.items()},
        "mapping_tuning": tuning, "chosen_alpha": chosen_alpha, "gate_alpha": gate_alpha,
        "max_validation_false_positive_rate": max_validation_false_positive_rate,
        "selected_gate": selected, "validation_gate_sweep": sweep,
        "summary": [summarize(rows, arm) for arm, rows in trials.items()], "trials": trials,
        "policy_array_bytes": policy.bytes,
        "interpretation": "Held-out intervention and family selection; no claim of task repair or calibrated probability.",
    }
    return report, policy, splits
