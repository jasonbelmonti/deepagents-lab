from __future__ import annotations

from typing import Any

import pytest

from deepagents_lab import agent


def test_create_agent_owns_deepagents_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled_graph = object()
    selected_models: list[str] = []

    def create_deep_agent(*, model: str) -> Any:
        selected_models.append(model)
        return compiled_graph

    monkeypatch.setattr(agent, "create_deep_agent", create_deep_agent)

    assert agent.create_agent("openai:test-model") is compiled_graph
    assert selected_models == ["openai:test-model"]


def test_default_model_remains_stable() -> None:
    assert agent.DEFAULT_MODEL == "openai:gpt-5.6-luna"
