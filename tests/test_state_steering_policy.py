import json

import numpy as np
import pytest
from langchain_core.messages import AIMessage

from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.state_steering.artifacts import load_policy, save_experiment
from deepagents_lab.experiments.state_steering.dataset import embed_examples
from deepagents_lab.experiments.state_steering.evaluation import evaluate
from deepagents_lab.experiments.state_steering.fixture import make_state_fixtures
from deepagents_lab.experiments.state_steering.gate import InterventionGate, select_threshold
from deepagents_lab.experiments.state_steering.revision import revise_once
from deepagents_lab.experiments.state_steering.runtime import check_state
from deepagents_lab.experiments.state_steering.splits import split_records
from deepagents_lab.experiments.state_steering.state import build_state


@pytest.fixture
def records():
    return embed_examples(make_state_fixtures(), LexicalEmbedder())


def test_gate_learns_intervention_on_new_states_and_threshold_can_abstain():
    states = [[-2, 1], [-2, -1], [2, 1], [2, -1]]
    gate = InterventionGate.fit(states, [False, False, True, True], alpha=0.01)
    scores = gate.scores([[-3, 0.2], [3, -0.2]])
    assert scores[0] < 0.5 < scores[1]
    chosen, _ = select_threshold([0.9, 0.1], [False, True], max_false_positive_rate=0)
    assert chosen["recall"] == 0 and chosen["interventions"] == 0 and chosen["precision"] is None


def test_group_splits_and_training_only_positive_correction_library(records):
    report, policy, splits = evaluate(records)
    groups = [set(report["split_group_ids"][name]) for name in splits]
    assert all(not groups[i] & groups[j] for i in range(3) for j in range(i))
    expected = {r.example.sample_id for r in splits["train"] if r.example.needs_intervention}
    assert {c["sample_id"] for c in policy.candidates} == expected
    assert all(c["family"] != "new-requirement" for c in policy.candidates)
    assert report["selected_gate"]["false_positive_rate"] <= 0.1
    for rows in report["trials"].values():
        assert all(row["candidate_id"] in expected for row in rows)


def test_test_targets_and_annotations_cannot_tune_policy(records):
    first, policy, _ = evaluate(records)
    test_ids = set(first["split_sample_ids"]["test"])
    changed = []
    for record in records:
        if record.example.sample_id in test_ids:
            example = record.example.model_copy(update={"problem": "Retrospective annotation replaced for the test."})
            record = record.model_copy(update={"example": example,
                                              "y": list(reversed(record.y)) if record.y is not None else None})
        changed.append(record)
    second, other, _ = evaluate(changed)
    assert first["chosen_alpha"] == second["chosen_alpha"]
    assert policy.threshold == other.threshold
    assert first["trials"] == second["trials"]
    assert np.array_equal(policy.mapping.weights, other.mapping.weights)

    # The intervention labels in the test set must not tune the gate either.
    target = next(r for r in records if r.example.sample_id in test_ids and r.example.needs_intervention)
    changed_label = target.model_copy(update={
        "example": target.example.model_copy(update={"needs_intervention": False}), "y": None,
    })
    _, label_policy, _ = evaluate([changed_label if r is target else r for r in records])
    assert policy.threshold == label_policy.threshold
    assert np.array_equal(policy.gate.weights, label_policy.gate.weights)


def test_unseen_test_families_count_as_misses(records):
    original, _, _ = evaluate(records)
    test_ids = set(original["split_sample_ids"]["test"])
    changed = [r.model_copy(update={"example": r.example.model_copy(update={"family": "unseen"})})
               if r.example.sample_id in test_ids and r.example.needs_intervention else r for r in records]
    report, _, _ = evaluate(changed)
    assert report["chosen_alpha"] == original["chosen_alpha"]
    assert all(r["supported_family_rate"] == 0 for r in report["summary"])
    assert all(r["positive_family_hit_at_1"] == 0 for r in report["summary"] if r["arm"] != "no_intervention")


def test_portable_policy_reload_preserves_runtime_decisions(records, tmp_path):
    report, policy, splits = evaluate(records)
    save_experiment(tmp_path, report, records, policy)
    loaded = load_policy(tmp_path / "policy.json")
    for record in splits["test"]:
        first = check_state(record.example.state, policy, LexicalEmbedder())
        second = check_state(record.example.state, loaded, LexicalEmbedder())
        assert first["intervene"] == second["intervene"]
        assert first["advice"] == second["advice"]
        assert first["gate_score"] == pytest.approx(second["gate_score"])
    with pytest.raises(ValueError, match="identity"):
        check_state(splits["test"][0].example.state, loaded, LexicalEmbedder(256))
    artifact = json.loads((tmp_path / "policy.json").read_text())
    artifact["state_format"] = "another-serializer"
    (tmp_path / "policy.json").write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match="Unsupported"):
        load_policy(tmp_path / "policy.json")


def test_runtime_embeds_only_once_and_reviser_obeys_gate_and_checkpoint(records):
    _, policy, splits = evaluate(records)
    state = splits["test"][0].example.state

    class CountingEmbedder(LexicalEmbedder):
        def embed(self, texts):
            assert len(texts) == 1
            self.count = getattr(self, "count", 0) + 1
            return super().embed(texts)

    class Model:
        def invoke(self, messages):
            self.messages = messages
            return AIMessage(content="An actual model response would appear here.")

    backend, model = CountingEmbedder(), Model()
    policy.threshold = 100
    skip = check_state(state, policy, backend)
    assert backend.count == 1 and not skip["intervene"]
    assert skip["timings"]["prediction_ms"] == skip["timings"]["retrieval_ms"] == 0
    result = revise_once(state, skip, model)
    assert not hasattr(model, "messages") and result["text"] == state.proposed_response
    policy.threshold = -100
    steer = check_state(state, policy, backend)
    assert backend.count == 2 and steer["intervene"] and steer["advice"]
    result = revise_once(state, steer, model)
    assert result["ok"] and result["revised"]
    payload = json.loads(model.messages[-1].content)
    assert payload["observable_state"] == state.model_dump()
    assert payload["candidate_advice"] == steer["advice"]
    different = build_state(state.history, "A different proposed response.")
    with pytest.raises(ValueError, match="different checkpoint"):
        revise_once(different, steer, model)


def test_evaluation_rejects_positive_only_and_mixed_backends(records):
    with pytest.raises(ValueError, match="both reviewed"):
        split_records([r for r in records if r.example.needs_intervention])
    records[0] = records[0].model_copy(update={"embedding_id": "another-space"})
    with pytest.raises(ValueError, match="one embedding backend"):
        split_records(records)
