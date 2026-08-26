from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage

from deepagents_lab import live


class FakeAgent:
    def __init__(self) -> None:
        self.input: dict[str, Any] | None = None

    def invoke(self, agent_input: dict[str, Any]) -> dict[str, list[AIMessage]]:
        self.input = agent_input
        return {"messages": [AIMessage(content="DEEPAGENTS_LIVE_OK")]}


def test_invoke_live_constructs_agent_and_returns_final_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_agent = FakeAgent()
    selected_model: list[str] = []

    def create_agent(*, model: str) -> FakeAgent:
        selected_model.append(model)
        return fake_agent

    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(live, "create_agent", create_agent)

    response = live.invoke_live("Return the sentinel.", model="openai:test-model")

    assert response == "DEEPAGENTS_LIVE_OK"
    assert selected_model == ["openai:test-model"]
    assert fake_agent.input == {
        "messages": [{"role": "user", "content": "Return the sentinel."}]
    }


def test_invoke_live_rejects_missing_key_before_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        live,
        "create_agent",
        lambda **_: pytest.fail("agent must not be constructed without a key"),
    )

    with pytest.raises(live.MissingApiKeyError, match="OPENAI_API_KEY is not set"):
        live.invoke_live("This must not reach a model.")


@pytest.mark.parametrize(
    ("environment_model", "arguments", "expected_model"),
    [
        (None, ["Return the sentinel."], live.DEFAULT_MODEL),
        (
            "openai:environment-model",
            ["Return the sentinel."],
            "openai:environment-model",
        ),
        (
            "openai:environment-model",
            ["--model", "openai:explicit-model", "Return the sentinel."],
            "openai:explicit-model",
        ),
    ],
)
def test_main_selects_model_and_prints_response(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    environment_model: str | None,
    arguments: list[str],
    expected_model: str,
) -> None:
    invocation: list[tuple[str, str]] = []

    def invoke(prompt: str, model: str) -> str:
        invocation.append((prompt, model))
        return "DEEPAGENTS_LIVE_OK"

    if environment_model is None:
        monkeypatch.delenv("DEEPAGENTS_LAB_MODEL", raising=False)
    else:
        monkeypatch.setenv("DEEPAGENTS_LAB_MODEL", environment_model)
    monkeypatch.setattr(live, "invoke_live", invoke)

    assert live.main(arguments) == 0
    assert invocation == [("Return the sentinel.", expected_model)]
    assert capsys.readouterr().out == "DEEPAGENTS_LIVE_OK\n"


def test_main_reports_missing_key_without_exposing_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert live.main(["This must not reach a model."]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "error: OPENAI_API_KEY is not set; export it in this shell before running.\n"
    )
