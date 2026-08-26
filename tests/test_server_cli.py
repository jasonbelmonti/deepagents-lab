from __future__ import annotations

import sys
from pathlib import Path

import pytest

from deepagents_lab import server_cli


class ExecCalled(RuntimeError):
    """Signal that the test double received the process replacement."""


def test_server_arguments_fix_the_local_server_coordinates() -> None:
    root = Path("/tmp/deepagents-lab")

    assert server_cli.server_arguments(root) == [
        sys.executable,
        "-m",
        "langgraph_cli",
        "dev",
        "--config",
        "/tmp/deepagents-lab/langgraph.json",
        "--host",
        "127.0.0.1",
        "--port",
        "2024",
        "--no-browser",
    ]


def test_main_runs_from_the_repository_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path("/tmp/deepagents-lab")
    changed_directories: list[Path] = []
    executions: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(server_cli, "repository_root", lambda: root)
    monkeypatch.setattr(server_cli.os, "chdir", changed_directories.append)

    def execv(executable: str, arguments: list[str]) -> None:
        executions.append((executable, arguments))
        raise ExecCalled

    monkeypatch.setattr(server_cli.os, "execv", execv)

    with pytest.raises(ExecCalled):
        server_cli.main()

    assert changed_directories == [root]
    assert executions == [(sys.executable, server_cli.server_arguments(root))]
