"""Separate intervention detection from correction-family selection."""
import numpy as np


def query_rows(policy, records, arm):
    states = [r.s for r in records]
    gate_scores = policy.gate.scores(states)
    scores, orders, _ = policy.rank(states, "ridge_prediction" if arm == "no_intervention" else arm)
    rows = []
    for record, gate_score, values, order in zip(records, gate_scores, scores, orders):
        example = record.example
        winner = policy.candidates[order[0]]
        matches = [rank for rank, i in enumerate(order, 1)
                   if example.needs_intervention and policy.candidates[i]["family"] == example.family]
        intervene = arm != "no_intervention" and bool(gate_score > policy.threshold)
        rows.append({
            "sample_id": example.sample_id, "needs_intervention": example.needs_intervention,
            "expected_family": example.family if example.needs_intervention else None,
            "intervene": intervene, "gate_score": float(gate_score),
            "candidate_id": winner["sample_id"], "predicted_family": winner["family"],
            "correction": winner["correction"] if intervene else None,
            "retrieval_score": float(values[order[0]]),
            "family_hit": bool(matches and matches[0] == 1),
            "reciprocal_rank": 1 / matches[0] if matches else 0.0,
            "supported_family": bool(matches),
        })
    return rows


def summarize(rows, arm):
    positives = [r for r in rows if r["needs_intervention"]]
    negatives = [r for r in rows if not r["needs_intervention"]]
    selected = [r for r in rows if r["intervene"]]

    def mean(items, key):
        return float(np.mean([r[key] for r in items])) if items else None

    return {
        "arm": arm, "queries": len(rows), "interventions": len(selected),
        "intervention_recall": mean(positives, "intervene"),
        "false_positive_rate": mean(negatives, "intervene"),
        "intervention_precision": mean(selected, "needs_intervention"),
        "useful_selection_precision": mean(selected, "family_hit"),
        "positive_family_hit_at_1": mean(positives, "family_hit") if arm != "no_intervention" else None,
        "positive_mrr": mean(positives, "reciprocal_rank") if arm != "no_intervention" else None,
        "supported_family_rate": mean(positives, "supported_family"),
        "selection_accuracy": float(np.mean([
            r["intervene"] and r["family_hit"] if r["needs_intervention"] else not r["intervene"] for r in rows
        ])),
    }
