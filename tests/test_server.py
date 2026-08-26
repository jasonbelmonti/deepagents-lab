from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from langgraph.pregel import Pregel

from deepagents_lab import server

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_langgraph_config_registers_one_local_graph() -> None:
    config = json.loads((REPOSITORY_ROOT / "langgraph.json").read_text())

    assert config["dependencies"] == ["."]
    assert config["graphs"] == {
        "deepagents_lab": "./src/deepagents_lab/server.py:graph"
    }
    assert "env" not in config
    assert "OPENAI_API_KEY" not in json.dumps(config)
    assert "LANGSMITH_API_KEY" not in json.dumps(config)


def test_server_export_reuses_shared_agent_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled_graph = object()
    monkeypatch.setattr(server, "create_agent", lambda: compiled_graph)

    assert server.graph() is compiled_graph


def test_server_module_import_is_keyless() -> None:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("LANGSMITH_API_KEY", None)
    environment["LANGSMITH_TRACING"] = "false"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from deepagents_lab.server import graph; print(callable(graph))",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.stdout == "True\n"
    assert result.stderr == ""


def test_server_factory_returns_a_compiled_graph_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    assert isinstance(server.graph(), Pregel)
