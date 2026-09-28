from hashlib import sha256
import json

import httpx
from langchain_openai import ChatOpenAI
import pytest

from deepagents_lab.experiments.steering.capture import CaptureStore
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.steering.evaluation import evaluate
from deepagents_lab.experiments.steering.fixture import make_fixtures
from deepagents_lab.experiments.steering.live import compare_revisions
from deepagents_lab.experiments.state_steering.revision import revise_once
from deepagents_lab.experiments.state_steering.state import state_from_event, state_text


@pytest.mark.parametrize("content,finish_reason,refusal,expected_ok", [
    ("", "length", None, False),
    (None, "stop", "Unable to provide a response.", False),
    ("A partially generated response", "length", None, False),
    ("The implementation is complete; the requested results remain unavailable.", "stop", None, True),
])
def test_both_revision_paths_record_provider_outcome_and_usage(
    tmp_path, content, finish_reason, refusal, expected_ok,
):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "test-completion", "object": "chat.completion", "created": 0, "model": "gpt-5.6-luna",
            "choices": [{"index": 0, "finish_reason": finish_reason,
                         "message": {"role": "assistant", "content": content, "refusal": refusal}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        })

    model = ChatOpenAI(model="gpt-5.6-luna", api_key="local-test", max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    store = CaptureStore(tmp_path / "capture", LexicalEmbedder())
    records = [store.accept(f.event, f.pair, origin="authored_fixture", capture_model="fixture")
               for f in make_fixtures()]
    _, index, splits = evaluate(records)
    query = splits["test"][0]
    rows = compare_revisions(query.event, index, [query.x], model, tmp_path / "revisions")
    assert json.loads((tmp_path / "revisions" / "revisions.json").read_text()) == rows
    state = state_from_event(query.event)
    decision = {"arm": "ridge_prediction", "intervene": True, "advice": "Report the available evidence accurately.",
                "state_sha256": sha256(state_text(state).encode()).hexdigest()}
    state_row = revise_once(state, decision, model)
    for row in [*rows, state_row]:
        assert row["ok"] is expected_ok
        assert row["usage"]["total_tokens"] == 30
        assert row["finish_reason"] == finish_reason and row["refusal"] == refusal
        if not expected_ok:
            assert row["error_type"] == "ValueError"
    if not expected_ok:
        assert state_row["text"] == state.proposed_response and not state_row["revised"]
    assert len(requests) == 5
