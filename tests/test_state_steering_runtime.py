import json

import httpx
from langchain_core.messages import AIMessage
from openai import OpenAI

from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder, OpenAIEmbedder
from deepagents_lab.experiments.state_steering.dataset import embed_examples
from deepagents_lab.experiments.state_steering.evaluation import evaluate
from deepagents_lab.experiments.state_steering.fixture import make_state_fixtures
from deepagents_lab.experiments.state_steering.revision import revise_once
from deepagents_lab.experiments.state_steering.runtime import check_state
from deepagents_lab.experiments.state_steering.state import state_text


def test_runtime_real_sdk_records_uncached_request_usage_then_cache_hit(tmp_path):
    requests = []
    lexical = LexicalEmbedder()

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        vectors = lexical.embed(body["input"])
        return httpx.Response(200, json={
            "object": "list", "model": body["model"],
            "data": [{"object": "embedding", "index": i, "embedding": vector.tolist()}
                     for i, vector in enumerate(vectors)],
            "usage": {"prompt_tokens": 80, "total_tokens": 80},
        })

    client = OpenAI(api_key="local-test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    backend = OpenAIEmbedder(client, tmp_path, dimensions=512)
    records = [r.model_copy(update={"embedding_id": backend.identity})
               for r in embed_examples(make_state_fixtures(), lexical)]
    _, policy, splits = evaluate(records)
    state = splits["test"][0].example.state
    cold = check_state(state, policy, backend)
    warm = check_state(state, policy, backend)
    assert len(requests) == 1 and requests[0]["input"] == [state_text(state)]
    assert cold["provider_requests"] == 1 and warm["provider_requests"] == 0
    assert cold["provider_calls"][0]["usage"]["total_tokens"] == 80
    assert cold["intervene"] == warm["intervene"] and cold["advice"] == warm["advice"]


def test_unusable_revision_keeps_usage_and_original_draft():
    records = embed_examples(make_state_fixtures(), LexicalEmbedder())
    _, policy, splits = evaluate(records)
    policy.threshold = -100
    state = splits["test"][0].example.state
    decision = check_state(state, policy, LexicalEmbedder())

    class EmptyModel:
        model_name = "local-test"

        def invoke(self, messages):
            return AIMessage(content="", usage_metadata={"input_tokens": 10, "output_tokens": 3, "total_tokens": 13})

    row = revise_once(state, decision, EmptyModel())
    assert not row["ok"] and not row["revised"] and row["error_type"] == "ValueError"
    assert row["text"] == state.proposed_response
    assert row["usage"]["total_tokens"] == 13 and row["model"] == "local-test"
