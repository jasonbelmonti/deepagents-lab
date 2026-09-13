"""Inspect the actual model boundary, including middleware-rendered PTC docs."""
import asyncio

import pytest
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from deepagents_lab.experiments.graph_ptc_value.config import ARMS, CASES, Config
from deepagents_lab.experiments.graph_ptc_value.fixture import make_graph
from deepagents_lab.experiments.graph_ptc_value.smoke import ScriptedModel
from deepagents_lab.experiments.graph_ptc_value.tools import GraphAPI
from deepagents_lab.experiments.graph_ptc_value.trial import run_trial


@pytest.mark.parametrize("arm", ARMS)
def test_complete_graph_contract_reaches_the_model_in_every_arm(arm):
    pytest.importorskip("langchain_quickjs")
    captured = {}

    class CaptureModel(ScriptedModel):
        def bind_tools(self, tools, **kwargs):
            captured["tools"] = {
                schema["function"]["name"]: schema["function"]
                for schema in map(convert_to_openai_tool, tools)
            }
            return self

        def _generate(self, messages, *args, **kwargs):
            captured["system"] = "\n".join(m.text for m in messages if isinstance(m, SystemMessage))
            return super()._generate(messages, *args, **kwargs)

    row = asyncio.run(run_trial(Config(), CASES[0], 7, arm, model=CaptureModel(responses=[AIMessage(content="[]")])))
    assert "error_type" not in row, row
    tools = GraphAPI(make_graph(7)).tools()
    # Ordinary provider definitions retain full descriptions. The PTC middleware
    # renders its own system API reference, which has historically dropped lines.
    for tool in tools:
        visible = captured["system"] if arm == "ptc" else captured["tools"][tool.name]["description"]
        assert tool.description in visible, f"{arm} lost part of {tool.name}'s contract"

    required = {
        "get_neighbors": ("source", "target", "kind", "last_seen", "inclusive", "default collaborated"),
        "get_profiles": ("person_id", "topic", "name", "default [topic]"),
        "get_contact_history": ("person_id", "last_contact", "inclusive", "An absent ID has not been contacted"),
    }
    for name, clauses in required.items():
        visible = captured["system"] if arm == "ptc" else captured["tools"][name]["description"]
        assert all(clause in visible for clause in (*clauses, "1–64", "No truncation or pagination")), (arm, name, visible)

    graph_names = {tool.name for tool in tools}
    assert ("eval" in captured["tools"]) == (arm != "ordinary")
    if arm == "ptc":
        assert graph_names.isdisjoint(captured["tools"])
        assert all(name in captured["system"] for name in ("tools.getNeighbors", "tools.getProfiles", "tools.getContactHistory"))
    else:
        assert graph_names <= captured["tools"].keys()
