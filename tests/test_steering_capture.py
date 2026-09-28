import json

import httpx
import numpy as np
from langchain_core.messages import AIMessage
from openai import OpenAI
import pytest

from deepagents_lab.experiments.steering.capture import CaptureStore, load_events
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder, OpenAIEmbedder
from deepagents_lab.experiments.steering.fixture import make_fixtures
from deepagents_lab.experiments.steering.live import capture_batch, capture_event, revision_messages


class RecordingModel:
    def __init__(self, response):
        self.response = response
        self.messages = None

    def bind_tools(self, tools, **kwargs):
        assert [t.name for t in tools] == ["accept_steering"]
        assert kwargs["tool_choice"] == "accept_steering"
        return self

    def invoke(self, messages):
        self.messages = messages
        return self.response


def test_tool_captures_pair_with_original_conversation_and_survives_reload(tmp_path):
    fixture = make_fixtures()[0]
    store = CaptureStore(tmp_path, LexicalEmbedder())
    tool = store.tool_for(fixture.event, origin="authored_fixture", capture_model="fixture")
    result = tool.invoke(fixture.pair.model_dump())
    assert result["problem"] == fixture.pair.problem
    record = CaptureStore(tmp_path, LexicalEmbedder()).read(fixture.event.event_id)
    assert record.event == fixture.event
    assert record.pair == fixture.pair
    assert np.allclose(np.linalg.norm(record.x), 1)
    assert tool.invoke(fixture.pair.model_dump()) == result
    with pytest.raises(ValueError, match="already exists"):
        tool.invoke({"problem": fixture.pair.problem, "correction": "An unrelated replacement correction."})


def test_model_sees_full_event_but_no_annotations_and_calls_real_tool(tmp_path):
    fixture = make_fixtures()[0]
    model = RecordingModel(AIMessage(content="", tool_calls=[{
        "id": "capture", "type": "tool_call", "name": "accept_steering", "args": fixture.pair.model_dump(),
    }]))
    store = CaptureStore(tmp_path, LexicalEmbedder())
    record = capture_event(fixture.event, store, model, "test-model")
    content = json.loads(model.messages[-1].content)
    assert content == [m.model_dump() for m in fixture.event.messages]
    assert fixture.event.family not in model.messages[-1].content
    assert record.origin == "model"
    assert record.capture_model == "test-model"
    assert json.loads((tmp_path / "attempts.jsonl").read_text())["ok"]


def test_failed_capture_is_logged_and_not_scored_as_a_record(tmp_path):
    fixture = make_fixtures()[0]
    store = CaptureStore(tmp_path, LexicalEmbedder())
    records, failures = capture_batch([fixture.event], store, RecordingModel(AIMessage(content="No tool.")), "test")
    assert not records
    assert failures == [{"event_id": fixture.event.event_id, "error_type": "ValueError"}]
    assert not (tmp_path / f"{fixture.event.event_id}.json").exists()
    assert json.loads((tmp_path / "attempts.jsonl").read_text())["ok"] is False


def test_revision_receives_prior_evidence_without_later_user_correction():
    event = make_fixtures()[0].event
    messages = revision_messages(event, "Inspect the saved evidence.")
    assert json.loads(messages[-1].content) == [m.model_dump() for m in event.messages[:-1]]
    assert event.messages[-1].content not in messages[-1].content


def test_real_sdk_embedding_contract_and_cache_identity(tmp_path):
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        return httpx.Response(200, json={
            "object": "list", "model": body["model"],
            "data": [{"object": "embedding", "index": i, "embedding": [1.0, float(i + 1)]}
                     for i in reversed(range(len(body["input"])))],
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        })

    client = OpenAI(api_key="local-test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    backend = OpenAIEmbedder(client, tmp_path, dimensions=2)
    vectors = backend.embed(["problem", "correction"])
    assert bodies[0]["input"] == ["problem", "correction"]
    assert bodies[0]["dimensions"] == 2
    assert np.allclose(vectors[0], np.array([1, 1]) / np.sqrt(2))
    assert backend.calls[0]["usage"]["total_tokens"] == 8
    assert np.allclose(backend.embed(["problem", "correction"]), vectors)
    assert len(bodies) == 1
    OpenAIEmbedder(client, tmp_path, model="another-model", dimensions=2).embed(["problem"])
    assert len(bodies) == 2


def test_import_rejects_duplicate_ids_and_unfinished_events(tmp_path):
    event = make_fixtures()[0].event
    path = tmp_path / "events.jsonl"
    path.write_text(event.model_dump_json() + "\n" + event.model_dump_json())
    with pytest.raises(ValueError, match="unique"):
        load_events(path)
    invalid = event.model_dump()
    invalid["messages"] = invalid["messages"][:-1]
    path.write_text(json.dumps(invalid))
    with pytest.raises(ValueError, match="steering message"):
        load_events(path)
