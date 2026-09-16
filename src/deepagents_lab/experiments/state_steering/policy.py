"""Train on S, gate interventions, and rank a training-only correction library."""
from dataclasses import dataclass
from time import perf_counter

import numpy as np

from ..steering.embeddings import normalized
from ..steering.predictor import RidgeMap
from .gate import InterventionGate
from .schema import STATE_FORMAT

ARMS = ("direct_correction", "state_neighbors", "ridge_prediction")


@dataclass
class StatePolicy:
    embedding_id: str
    states: np.ndarray
    corrections: np.ndarray
    candidates: list[dict]
    mapping: RidgeMap
    gate: InterventionGate
    threshold: float = 0.5
    state_format: str = STATE_FORMAT

    @classmethod
    def fit(cls, training, alpha=1.0, gate_alpha=1.0):
        if len({r.embedding_id for r in training}) != 1:
            raise ValueError("Training requires one embedding identity.")
        positives = [r for r in training if r.example.needs_intervention]
        if len(positives) < 2:
            raise ValueError("At least two positive training examples are required.")
        states = normalized([r.s for r in positives])
        corrections = normalized([r.y for r in positives])
        candidates = [{"sample_id": r.example.sample_id, "family": r.example.family,
                       "correction": r.example.correction} for r in positives]
        return cls(training[0].embedding_id, states, corrections, candidates,
                   RidgeMap.fit(states, corrections, alpha),
                   InterventionGate.fit([r.s for r in training],
                                        [r.example.needs_intervention for r in training], gate_alpha))

    def rank(self, states, arm="ridge_prediction"):
        if arm not in ARMS:
            raise ValueError(f"Unknown arm: {arm}")
        started = perf_counter()
        states = normalized(states)
        query = self.mapping.predict(states) if arm == "ridge_prediction" else states
        prediction_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        scores = query @ (self.states if arm == "state_neighbors" else self.corrections).T
        order = np.argsort(-scores, axis=1, kind="stable")
        return scores, order, {"prediction_ms": prediction_ms,
                               "retrieval_ms": (perf_counter() - started) * 1000}

    @property
    def bytes(self):
        return self.mapping.bytes + self.gate.weights.nbytes + self.states.nbytes + self.corrections.nbytes
