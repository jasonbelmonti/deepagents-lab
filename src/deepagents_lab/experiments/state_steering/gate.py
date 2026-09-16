"""Small binary ridge scorer; its output is a score, not a calibrated probability."""
from dataclasses import dataclass

import numpy as np

from ..steering.embeddings import normalized


@dataclass
class InterventionGate:
    weights: np.ndarray
    intercept: float

    @classmethod
    def fit(cls, states, labels, alpha=1.0):
        states, labels = normalized(states), np.asarray(labels, dtype=float)
        if labels.shape != (len(states),) or set(labels) != {0.0, 1.0}:
            raise ValueError("Gate training requires both reviewed intervention and no-intervention examples.")
        if not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("Gate regularization must be positive and finite.")
        mean = states.mean(axis=0)
        centered = states - mean
        weights = centered.T @ np.linalg.solve(centered @ centered.T + alpha * np.eye(len(states)),
                                               labels - labels.mean())
        return cls(weights, float(labels.mean() - mean @ weights))

    def scores(self, states):
        return normalized(states) @ self.weights + self.intercept


def threshold_sweep(scores, labels):
    scores, labels = np.asarray(scores), np.asarray(labels, dtype=bool)
    if scores.shape != labels.shape or not np.isfinite(scores).all() or len(set(labels)) != 2:
        raise ValueError("Threshold tuning requires finite scores and both label classes.")
    values = np.unique(scores)
    thresholds = [float(np.nextafter(values[0], -np.inf)),
                  *[float(a + (b - a) / 2) for a, b in zip(values, values[1:])], float(values[-1])]
    rows = []
    for threshold in thresholds:
        accepted = scores > threshold
        rows.append({"threshold": threshold, "recall": float(accepted[labels].mean()),
                     "false_positive_rate": float(accepted[~labels].mean()),
                     "precision": float(labels[accepted].mean()) if accepted.any() else None,
                     "interventions": int(accepted.sum())})
    return rows


def select_threshold(scores, labels, max_false_positive_rate):
    if not 0 <= max_false_positive_rate <= 1:
        raise ValueError("Maximum validation false-positive rate must be between zero and one.")
    rows = threshold_sweep(scores, labels)
    eligible = [r for r in rows if r["false_positive_rate"] <= max_false_positive_rate]
    chosen = max(eligible, key=lambda r: (r["recall"], -r["false_positive_rate"], r["threshold"]))
    return chosen, rows
