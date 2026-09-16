import numpy as np
import pytest

from deepagents_lab.experiments.steering.capture import CaptureStore
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.steering.evaluation import evaluate, margin_sweep, split_records
from deepagents_lab.experiments.steering.fixture import make_fixtures
from deepagents_lab.experiments.steering.predictor import RidgeMap


@pytest.fixture
def records(tmp_path):
    store = CaptureStore(tmp_path, LexicalEmbedder())
    return [store.accept(f.event, f.pair, origin="authored_fixture", capture_model="fixture") for f in make_fixtures()]


def test_ridge_learns_non_identity_mapping_on_unseen_inputs():
    rng = np.random.default_rng(103)
    train = rng.normal(size=(40, 3))
    rotation = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]])
    query = rng.normal(size=(12, 3))
    expected = query @ rotation
    expected /= np.linalg.norm(expected, axis=1, keepdims=True)
    predicted = RidgeMap.fit(train, train @ rotation, alpha=0.0001).predict(query)
    assert np.allclose(predicted, expected, atol=1e-4)
    assert not np.allclose(query / np.linalg.norm(query, axis=1, keepdims=True), expected, atol=0.1)


def test_grouped_holdout_and_training_only_correction_library(records):
    report, index, splits = evaluate(records)
    groups = [set(report["split_group_ids"][name]) for name in ("train", "validation", "test")]
    assert all(not groups[i] & groups[j] for i in range(3) for j in range(i))
    training_ids = {r.event.event_id for r in splits["train"]}
    assert {r.event.event_id for r in index.records} == training_ids
    assert all(row["candidate_id"] in training_ids for rows in report["trials"].values() for row in rows)
    assert sum(len(values) for values in splits.values()) == len(records)


def test_test_targets_do_not_select_regularization(records):
    first, _, _ = evaluate(records)
    ids = set(first["split_event_ids"]["test"])
    changed = [r.model_copy(update={"y": list(reversed(r.y))}) if r.event.event_id in ids else r for r in records]
    second, _, _ = evaluate(changed)
    assert first["chosen_alpha"] == second["chosen_alpha"]
    assert first["trials"] == second["trials"]


def test_unseen_family_counts_as_miss_and_zero_coverage_has_no_precision(records):
    report, _, _ = evaluate(records)
    ids = set(report["split_event_ids"]["test"])
    changed = [r.model_copy(update={"event": r.event.model_copy(update={"family": "unseen"})})
               if r.event.event_id in ids else r for r in records]
    result, index, splits = evaluate(changed)
    assert all(row["supported_family"] == 0 and row["hit_at_1"] == 0 for row in result["summary"])
    sweep = margin_sweep(index, splits["validation"], thresholds=(3.0,))
    assert sweep[0]["coverage"] == 0
    assert sweep[0]["family_precision"] is None


def test_mixed_embedding_spaces_are_rejected(records):
    records[0] = records[0].model_copy(update={"embedding_id": "different-space"})
    with pytest.raises(ValueError, match="one embedding backend"):
        split_records(records)
