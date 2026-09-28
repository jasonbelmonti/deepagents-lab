"""Group holdouts established before training or threshold selection."""
import numpy as np

from .dataset import validate_examples


def split_records(records, seed=42):
    records = list(records)
    validate_examples([r.example for r in records])
    if len({(r.embedding_id, len(r.s)) for r in records}) != 1:
        raise ValueError("Use one embedding backend and dimension throughout the corpus.")
    groups = sorted({r.example.group_id for r in records})
    if len(groups) < 5:
        raise ValueError("Use at least five independent task/conversation groups.")
    np.random.default_rng(seed).shuffle(groups)
    size = max(1, len(groups) // 5)
    assignments = {g: "test" if i < size else "validation" if i < 2 * size else "train"
                   for i, g in enumerate(groups)}
    splits = {name: [r for r in records if assignments[r.example.group_id] == name]
              for name in ("train", "validation", "test")}
    for name, rows in splits.items():
        if {r.example.needs_intervention for r in rows} != {False, True}:
            raise ValueError(f"{name} requires both reviewed intervention and no-intervention examples.")
    return splits
