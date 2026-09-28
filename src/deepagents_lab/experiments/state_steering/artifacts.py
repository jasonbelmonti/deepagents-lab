"""Portable JSON policy artifacts and reproducible experiment evidence."""
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np

from ..steering.embeddings import normalized
from ..steering.predictor import RidgeMap
from .gate import InterventionGate
from .policy import StatePolicy
from .schema import STATE_FORMAT


def save_policy(path, policy):
    data = {
        "artifact_version": 1, "embedding_id": policy.embedding_id, "state_format": policy.state_format,
        "threshold": policy.threshold, "states": policy.states.tolist(),
        "corrections": policy.corrections.tolist(), "candidates": policy.candidates,
        "mapping": {name: getattr(policy.mapping, name).tolist()
                    for name in ("x_mean", "y_mean", "anchors", "weights")},
        "alpha": policy.mapping.alpha,
        "gate": {"weights": policy.gate.weights.tolist(), "intercept": policy.gate.intercept},
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False))
    return path


def load_policy(path):
    data = json.loads(Path(path).read_text())
    if data["artifact_version"] != 1 or data["state_format"] != STATE_FORMAT:
        raise ValueError("Unsupported policy artifact or state format.")
    states, corrections = normalized(data["states"]), normalized(data["corrections"])
    mapping = RidgeMap(**{name: np.asarray(value, dtype=float) for name, value in data["mapping"].items()},
                       alpha=data["alpha"])
    gate = InterventionGate(np.asarray(data["gate"]["weights"], dtype=float), data["gate"]["intercept"])
    n, d = states.shape
    if (corrections.shape != (n, d) or len(data["candidates"]) != n
            or mapping.x_mean.shape != (d,) or mapping.y_mean.shape != (d,)
            or mapping.anchors.shape != (n, d) or mapping.weights.shape != (n, d)
            or gate.weights.shape != (d,)):
        raise ValueError("Policy artifact dimensions disagree.")
    arrays = [mapping.x_mean, mapping.y_mean, mapping.anchors, mapping.weights, gate.weights,
              [gate.intercept, data["threshold"], mapping.alpha]]
    if not all(np.isfinite(a).all() for a in arrays) or mapping.alpha <= 0:
        raise ValueError("Policy parameters must be finite with positive regularization.")
    return StatePolicy(data["embedding_id"], states, corrections, data["candidates"], mapping, gate,
                       data["threshold"], data["state_format"])


def save_experiment(directory, report, records, policy):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    corpus = "\n".join(r.model_dump_json() for r in records) + "\n"
    (directory / "embedded.jsonl").write_text(corpus)
    (directory / "examples.jsonl").write_text("\n".join(r.example.model_dump_json() for r in records) + "\n")
    (directory / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    policy_path = save_policy(directory / "policy.json", policy)
    root = Path(__file__).parent.parent
    sources = sorted([*Path(__file__).parent.glob("*.py"), *(root / "steering").glob("*.py")])
    manifest = {
        "python": sys.version,
        "versions": {name: version(name) for name in ("numpy", "deepagents", "langchain-openai", "openai")},
        "corpus_sha256": sha256(corpus.encode()).hexdigest(),
        "policy_sha256": sha256(policy_path.read_bytes()).hexdigest(),
        "source_sha256": {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sources},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return directory
