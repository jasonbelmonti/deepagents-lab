import json

import pytest

from deepagents_lab.experiments.steering.capture import CaptureStore
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.steering.fixture import make_fixtures
from deepagents_lab.experiments.state_steering.dataset import embed_examples, from_capture, load_examples
from deepagents_lab.experiments.state_steering.fixture import make_state_fixtures
from deepagents_lab.experiments.state_steering.schema import EmbeddedState, StateExample
from deepagents_lab.experiments.state_steering.state import build_state, state_from_event, state_text


class RecordingEmbedder(LexicalEmbedder):
    def __init__(self):
        super().__init__()
        self.inputs = []

    def embed(self, texts):
        self.inputs.extend(texts)
        return super().embed(texts)


def test_historical_state_matches_runtime_and_excludes_later_feedback_and_annotations(tmp_path):
    fixture = make_fixtures()[0]
    event_data = fixture.event.model_dump()
    event_data["messages"][-1]["content"] = "PRIVATE FUTURE CORRECTION only known after this checkpoint."
    event = type(fixture.event).model_validate(event_data)
    store = CaptureStore(tmp_path, LexicalEmbedder())
    captured = store.accept(event, fixture.pair, origin="authored_fixture", capture_model="fixture")
    example = from_capture(captured, needs_intervention=True, assessment="Reviewed original requirement was unmet.")
    runtime = build_state(event.messages[:-2], event.messages[-2].content)
    assert state_text(example.state) == state_text(runtime)
    backend = RecordingEmbedder()
    embed_examples([example], backend)
    assert backend.inputs == [state_text(runtime), fixture.pair.correction]
    assert "PRIVATE FUTURE CORRECTION" not in " ".join(backend.inputs)
    assert fixture.pair.problem not in " ".join(backend.inputs)
    assert example.group_id not in backend.inputs[0]
    with pytest.raises(TypeError, match="ObservableState"):
        state_text(example)


def test_later_scope_change_preserves_annotation_without_becoming_a_training_action(tmp_path):
    fixture = next(f for f in make_fixtures() if f.event.family == "new-requirement")
    captured = CaptureStore(tmp_path, LexicalEmbedder()).accept(
        fixture.event, fixture.pair, origin="authored_fixture", capture_model="fixture")
    example = from_capture(captured, needs_intervention=False, assessment="New requirement was not present at this checkpoint.")
    backend = RecordingEmbedder()
    record = embed_examples([example], backend)[0]
    assert example.problem == fixture.pair.problem
    assert example.correction == fixture.pair.correction
    assert record.y is None
    assert backend.inputs == [state_text(example.state)]


def test_annotations_cannot_change_state_embedding():
    example = make_state_fixtures()[0]
    changed = example.model_copy(update={"problem": "A completely different retrospective problem annotation."})
    first = embed_examples([example], LexicalEmbedder())[0]
    second = embed_examples([changed], LexicalEmbedder())[0]
    assert first.s == second.s and first.y == second.y


def test_import_requires_reviewed_labels_and_rejects_duplicate_states(tmp_path):
    example = make_state_fixtures()[0]
    path = tmp_path / "examples.jsonl"
    missing_label = example.model_dump()
    del missing_label["needs_intervention"]
    path.write_text(json.dumps(missing_label))
    with pytest.raises(ValueError, match="needs_intervention"):
        load_examples(path)
    duplicate = example.model_copy(update={"sample_id": "different-id", "group_id": "different-group"})
    path.write_text(example.model_dump_json() + "\n" + duplicate.model_dump_json())
    with pytest.raises(ValueError, match="Duplicate observable"):
        load_examples(path)
    with pytest.raises(ValueError, match="require problem"):
        StateExample.model_validate({**example.model_dump(), "correction": None})


def test_oversize_state_fails_before_any_embedding_request():
    examples = make_state_fixtures()[:2]
    large = build_state(examples[1].state.history, "large " * 2000)
    examples[1] = examples[1].model_copy(update={"state": large})
    backend = RecordingEmbedder()
    with pytest.raises(ValueError, match="no truncation"):
        embed_examples(examples, backend)
    assert not backend.inputs


def test_invalid_capture_checkpoint_and_negative_target_are_rejected():
    event = make_fixtures()[0].event
    data = event.model_dump()
    data["messages"][-2]["role"] = "tool"
    with pytest.raises(ValueError, match="assistant response"):
        state_from_event(type(event).model_validate(data))
    negative = make_state_fixtures()[1]
    with pytest.raises(ValueError, match="Only intervention"):
        EmbeddedState(example=negative, embedding_id="test", s=[1, 0], y=[0, 1])
