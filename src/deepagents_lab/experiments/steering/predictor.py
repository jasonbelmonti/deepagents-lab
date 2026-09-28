"""A regularized linear X→Y predictor and explicit retrieval alternatives."""
from dataclasses import dataclass

import numpy as np

from .embeddings import normalized


@dataclass
class RidgeMap:
    x_mean: np.ndarray
    y_mean: np.ndarray
    anchors: np.ndarray
    weights: np.ndarray
    alpha: float

    @classmethod
    def fit(cls, x, y, alpha=1.0):
        x, y = normalized(x), normalized(y)
        if len(x) != len(y) or len(x) < 2 or not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("Fit needs aligned rows and a positive finite regularization strength.")
        x_mean, y_mean = x.mean(axis=0), y.mean(axis=0)
        anchors = x - x_mean
        # Dual form avoids a dimensions×dimensions solve for small datasets.
        weights = np.linalg.solve(anchors @ anchors.T + alpha * np.eye(len(x)), y - y_mean)
        return cls(x_mean, y_mean, anchors, weights, float(alpha))

    def predict(self, x):
        return normalized((normalized(x) - self.x_mean) @ self.anchors.T @ self.weights + self.y_mean)

    @property
    def bytes(self):
        return sum(array.nbytes for array in (self.x_mean, self.y_mean, self.anchors, self.weights))


class CorrectionIndex:
    def __init__(self, training_records, alpha=1.0):
        self.records = list(training_records)
        self.x = normalized([record.x for record in self.records])
        self.y = normalized([record.y for record in self.records])
        self.mapping = RidgeMap.fit(self.x, self.y, alpha)

    def scores(self, query_x, arm):
        query_x = normalized(query_x)
        if arm == "problem_neighbors":
            return query_x @ self.x.T
        if arm == "direct_correction":
            return query_x @ self.y.T
        if arm == "ridge_prediction":
            return self.mapping.predict(query_x) @ self.y.T
        raise ValueError(f"Unknown retrieval arm: {arm}")

    def recommend(self, query_x, arm="ridge_prediction", limit=3):
        scores = self.scores(query_x, arm)[0]
        order = np.argsort(-scores, kind="stable")[:limit]
        return [
            {"event_id": self.records[i].event.event_id, "family": self.records[i].event.family,
             "correction": self.records[i].pair.correction, "score": float(scores[i])}
            for i in order
        ]
