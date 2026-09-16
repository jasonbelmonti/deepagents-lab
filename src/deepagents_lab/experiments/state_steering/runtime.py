"""Host-facing checkpoint check: one state embedding, optional prediction/retrieval."""
from hashlib import sha256
from time import perf_counter

from .policy import ARMS
from .state import state_text


def check_state(state, policy, embedder, *, arm="ridge_prediction", limit=3):
    if embedder.identity != policy.embedding_id or state.format != policy.state_format:
        raise ValueError("Runtime state format and embedding identity must match training.")
    if arm not in ARMS or limit < 1:
        raise ValueError("Choose a supported arm and positive candidate limit.")
    started = perf_counter()
    text = state_text(state)
    timings = {"serialization_ms": (perf_counter() - started) * 1000}
    prior_calls = len(getattr(embedder, "calls", []))
    embedded_at = perf_counter()
    vector = embedder.embed([text])
    timings["embedding_ms"] = (perf_counter() - embedded_at) * 1000
    gate_at = perf_counter()
    score = float(policy.gate.scores(vector)[0])
    intervene = score > policy.threshold
    timings["gate_ms"] = (perf_counter() - gate_at) * 1000
    timings.update(prediction_ms=0.0, retrieval_ms=0.0)
    candidates = []
    if intervene:
        scores, order, rank_timings = policy.rank(vector, arm)
        timings.update(rank_timings)
        candidates = [{**policy.candidates[i], "score": float(scores[0, i])} for i in order[0, :limit]]
    timings["total_check_ms"] = (perf_counter() - started) * 1000
    calls = getattr(embedder, "calls", [])[prior_calls:]
    return {
        "intervene": intervene, "advice": candidates[0]["correction"] if candidates else None,
        "gate_score": score, "threshold": policy.threshold, "candidates": candidates, "arm": arm,
        "state_sha256": sha256(text.encode()).hexdigest(), "state_bytes": len(text.encode()),
        "embedding_id": embedder.identity, "provider_requests": len(calls),
        "provider_calls": calls, "timings": timings,
    }
