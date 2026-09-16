from hashlib import sha256
import json

import pytest

from deepagents_lab.experiments.steering.capture import CaptureStore, load_events
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.steering.schema import Message, SteeringPair
from deepagents_lab.experiments.state_steering.dataset import from_capture
from deepagents_lab.experiments.state_steering.revision import revise_once
from deepagents_lab.experiments.state_steering.state import build_state, state_text


def test_import_capture_conversion_and_conflict_check_preserve_source_text(tmp_path):
    source = "    first()\n    second()\n"
    correction = "    corrected_first()\n    corrected_second()\n"
    data = {"event_id": "indented", "group_id": "task", "family": "code-format",
            "messages": [{"role": "user", "content": "Supply an indented Python suite."},
                         {"role": "assistant", "content": source},
                         {"role": "user", "content": "Correct the function names."}]}
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(data))
    event = load_events(path)[0]
    pair = SteeringPair(problem="The supplied function names need correction.", correction=correction)
    store = CaptureStore(tmp_path / "capture", LexicalEmbedder())
    captured = store.accept(event, pair, origin="authored_fixture", capture_model="fixture")
    assert store.read("indented").event.messages[1].content == source
    assert captured.pair.correction == correction
    example = from_capture(captured, needs_intervention=True, assessment="The request specified different function names.")
    assert example.state.proposed_response == source and example.correction == correction
    data["messages"][1]["content"] = source.strip()
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="already exists"):
        store.accept(load_events(path)[0], pair, origin="authored_fixture", capture_model="fixture")


def test_no_intervention_returns_exact_draft_including_code_indentation():
    source = "    first()\n    second()\n"
    state = build_state([{"role": "user", "content": "Return the indented Python suite."}], source)
    assert json.loads(state_text(state))["proposed_response"] == source
    decision = {"arm": "ridge_prediction", "intervene": False, "advice": None,
                "state_sha256": sha256(state_text(state).encode()).hexdigest()}
    result = revise_once(state, decision, object())
    assert result["ok"] and not result["revised"] and result["text"] == source
    compile("if True:\n" + result["text"], "returned-suite", "exec")


def test_whitespace_only_fields_remain_invalid():
    with pytest.raises(ValueError):
        Message(role="assistant", content=" \n\t ")
    with pytest.raises(ValueError):
        build_state([{"role": "user", "content": "Return the code."}], "   ")
